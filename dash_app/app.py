from dash import Dash, html, dcc, Input, Output, State, dash_table, dash
import dash_bootstrap_components as dbc
import pandas as pd
import dash
import sqlite3
from datetime import datetime
import plotly.graph_objects as go
from db import (insert_set, delete_set, insert_or_update_target, get_all_targets, delete_target, 
                add_person, add_exercise, get_all_people, get_all_exercises_from_db, DB_PATH)

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)

def get_all_exercises():
    return get_all_exercises_from_db()

def get_today_progress(person):
    """Get today's progress for a person against their targets"""
    conn = sqlite3.connect(DB_PATH)
    
    # Get targets for this person
    targets_df = pd.read_sql_query(
        "SELECT exercise, target_reps FROM daily_targets WHERE person = ?", 
        conn, params=[person]
    )
    
    # Get today's workouts
    today = datetime.now().strftime('%Y-%m-%d')
    workouts_df = pd.read_sql_query(
        "SELECT exercise, SUM(repetitions) as total_reps FROM workout_sets WHERE person = ? AND DATE(timestamp) = ? GROUP BY exercise",
        conn, params=[person, today]
    )
    
    conn.close()
    
    if targets_df.empty:
        return []
    
    # Merge targets with actual workouts
    progress = []
    for _, target_row in targets_df.iterrows():
        exercise = target_row['exercise']
        target = target_row['target_reps']
        
        workout_row = workouts_df[workouts_df['exercise'] == exercise]
        actual = workout_row['total_reps'].values[0] if not workout_row.empty else 0
        
        percentage = min(100, (actual / target * 100)) if target > 0 else 0
        
        progress.append({
            'exercise': exercise,
            'actual': int(actual),
            'target': int(target),
            'percentage': round(percentage, 1)
        })
    
    return progress

def create_progress_chart(exercise, actual, target, percentage):
    """Create a circular progress chart using pie chart"""
    # Ensure we always have values that sum to 100
    filled = min(percentage, 100)
    remaining = 100 - filled
    
    colors = ['#E879F9' if percentage >= 100 else '#B794F6', 'rgba(255,255,255,0.1)']
    
    fig = go.Figure(data=[go.Pie(
        values=[filled, remaining],
        hole=0.7,
        marker=dict(colors=colors, line=dict(color='#303030', width=2)),
        textinfo='none',
        hoverinfo='skip',
        showlegend=False,
        direction='clockwise',
        sort=False
    )])
    
    # Add text in the center
    fig.add_annotation(
        text=f"{int(percentage)}%",
        x=0.5, y=0.5,
        font=dict(size=24, color='white', family='Arial Black'),
        showarrow=False,
        xref="paper",
        yref="paper"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=180,
        width=180,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False
    )
    
    return fig

def load_data(person=None):
    conn = sqlite3.connect(DB_PATH)
    if person:
        query = f"SELECT * FROM workout_sets WHERE person = ? ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn, params=[person])
    else:
        df = pd.read_sql_query("SELECT * FROM workout_sets ORDER BY timestamp DESC", conn)
    conn.close()
    
    if df.empty:
        return df
    
    # Convert timestamp and format date
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp_dt'].dt.strftime('%d.%m.%Y')
    df = df.sort_values('timestamp_dt', ascending=False)
    
    # Get unique dates sorted
    unique_dates = df['date'].unique()
    
    result_rows = []
    
    for idx, date in enumerate(unique_dates):
        date_data = df[df['date'] == date]
        exercises = []
        reps_display = []
        
        # Track how many times we've seen each exercise on the current day
        exercise_count = {}
        
        for _, row in date_data.iterrows():
            exercise = row['exercise']
            current_reps = row['repetitions']
            
            # Track which occurrence of this exercise we're on
            if exercise not in exercise_count:
                exercise_count[exercise] = 0
            occurrence_index = exercise_count[exercise]
            exercise_count[exercise] += 1
            
            # Find the same exercise on the previous day (matching occurrence)
            if idx < len(unique_dates) - 1:
                prev_date = unique_dates[idx + 1]
                prev_data = df[(df['date'] == prev_date) & (df['exercise'] == exercise)]
                
                if not prev_data.empty and occurrence_index < len(prev_data):
                    prev_reps = prev_data.iloc[occurrence_index]['repetitions']
                    if current_reps > prev_reps:
                        increase = ((current_reps - prev_reps) / prev_reps) * 100
                        reps_display.append(f"🟢 {current_reps} (+{increase:.0f}%)")
                    elif current_reps < prev_reps:
                        decrease = ((prev_reps - current_reps) / prev_reps) * 100
                        reps_display.append(f"🔴 {current_reps} (-{decrease:.0f}%)")
                    else:
                        reps_display.append(f"⚪ {current_reps} (+0%)")
                else:
                    reps_display.append(str(current_reps))
            else:
                reps_display.append(str(current_reps))
            
            exercises.append(exercise)
        
        result_rows.append({
            'date': date,
            'exercise': ', '.join(exercises),
            'repetitions': ', '.join(reps_display),
            'id': date_data.iloc[0]['id']
        })
    
    return pd.DataFrame(result_rows)

# -------------------------------------------------------------
# LAYOUT
# -------------------------------------------------------------
app.layout = dbc.Container([

    html.Div([
        html.H1("💪 Workout Tracker", className="text-center mb-0", style={
            "color": "#B794F6", 
            "fontWeight": "bold",
            "textShadow": "0 0 20px rgba(183, 148, 246, 0.4)",
            "fontSize": "2.5rem"
        }),
        html.P("Verfolge deine Fortschritte und erreiche deine Ziele", 
               className="text-center text-muted", 
               style={"fontSize": "1rem", "marginTop": "10px"})
    ], className="mt-4 mb-4"),

    dbc.Tabs([
        dbc.Tab(label="📊 Workout Einträge", tab_id="tab-workouts", tab_style={"marginLeft": "10px"}),
        dbc.Tab(label="🎯 Ziele verwalten", tab_id="tab-targets"),
    ], id="tabs", active_tab="tab-workouts", className="mb-3"),

    html.Div(id="tab-content", className="mt-3"),
    
    dcc.Interval(id="interval", interval=2000, n_intervals=0)

], fluid=True, style={"maxWidth": "1400px"})

# -------------------------------------------------------------
# TAB CONTENT
# -------------------------------------------------------------
workout_tab = html.Div([
    # INPUT AREA
    dbc.Card([
        dbc.CardHeader([
            html.H4("➕ Neuer Workout-Eintrag", className="mb-0", style={"color": "white"})
        ], style={"backgroundColor": "#1e1e1e"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("👤 Person", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="person",
                        options=[],
                        placeholder="Person wählen",
                        className="mt-1"
                    )
                ], xs=12, md=4),

                dbc.Col([
                    html.Label("🏋️ Übung", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="exercise",
                        options=[],
                        placeholder="Übung wählen",
                        searchable=True,
                        clearable=True,
                        className="mt-1",
                        style={"width": "100%"}
                    )
                ], xs=12, md=4),

                dbc.Col([
                    html.Label("🔢 Wiederholungen", style={"fontWeight": "bold"}),
                    dcc.Input(
                        id="reps",
                        type="number",
                        placeholder="12",
                        className="form-control mt-1"
                    )
                ], xs=12, md=4),
            ]),

            dbc.Row([
                dbc.Col([
                    html.Label("📅 Datum", style={"fontWeight": "bold"}),
                    dcc.DatePickerSingle(
                        id="date-picker",
                        date=None,
                        placeholder="Datum wählen",
                        display_format="DD.MM.YYYY",
                        className="mt-1",
                        style={"width": "100%"}
                    )
                ], xs=12, md=4),
            ], className="mt-3"),

            dbc.Button("✅ Eintrag hinzufügen", id="add-btn", color="info", size="lg", className="mt-3 w-100", 
                      style={"fontWeight": "bold"}),

            html.Div(id="output", className="mt-3 text-success", style={"fontSize": "1.1rem", "fontWeight": "bold"}),
        ], style={"backgroundColor": "#2b3035"})
    ], className="mb-5 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"}),

    # SECTIONS FOR EACH PERSON
    html.Div([
        html.Hr(style={"borderTop": "2px solid #E879F9", "marginTop": "40px", "marginBottom": "30px"}),
        html.H3("👥 Einträge pro Person", className="text-center mb-4", style={"color": "#E879F9", "fontWeight": "bold"})
    ]),
    html.Div(id="people-sections")
])

targets_tab = html.Div([
    # Add New Person Section
    dbc.Card([
        dbc.CardHeader([
            html.H4("👤 Neue Person hinzufügen", className="mb-0", style={"color": "white"})
        ], style={"backgroundColor": "#1e1e1e"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Name", style={"fontWeight": "bold"}),
                    dcc.Input(
                        id="new-person-name",
                        type="text",
                        placeholder="Name eingeben",
                        className="form-control mt-1"
                    )
                ], xs=12, md=8),
                dbc.Col([
                    dbc.Button("➕ Hinzufügen", id="add-person-btn", color="success", className="mt-4 w-100", style={"fontWeight": "bold"}),
                ], xs=12, md=4),
            ]),
            html.Div(id="person-output", className="mt-3 text-success", style={"fontSize": "1rem", "fontWeight": "bold"}),
        ], style={"backgroundColor": "#2b3035"})
    ], className="mb-4 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"}),

    # Add New Exercise Section
    dbc.Card([
        dbc.CardHeader([
            html.H4("🏋️ Neue Übung hinzufügen", className="mb-0", style={"color": "white"})
        ], style={"backgroundColor": "#1e1e1e"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Übung"),
                    html.Label("Übung", style={"fontWeight": "bold"}),
                    dcc.Input(
                        id="new-exercise-name",
                        type="text",
                        placeholder="Übungsname eingeben",
                        className="form-control mt-1"
                    )
                ], xs=12, md=8),
                dbc.Col([
                    dbc.Button("➕ Hinzufügen", id="add-exercise-btn", color="success", className="mt-4 w-100", style={"fontWeight": "bold"}),
                ], xs=12, md=4),
            ]),
            html.Div(id="exercise-output", className="mt-3 text-success", style={"fontSize": "1rem", "fontWeight": "bold"}),
        ], style={"backgroundColor": "#2b3035"})
    ], className="mb-4 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"}),

    # Add Target Section
    dbc.Card([
        dbc.CardHeader([
            html.H4("🎯 Neues Ziel hinzufügen", className="mb-0", style={"color": "white"})
        ], style={"backgroundColor": "#1e1e1e"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("👤 Person", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="target-person",
                        options=[],
                        placeholder="Person wählen",
                        className="mt-1"
                    )
                ], xs=12, md=4),

                dbc.Col([
                    html.Label("🏋️ Übung", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="target-exercise",
                        options=[],
                        placeholder="Übung wählen",
                        searchable=True,
                        clearable=True,
                        className="mt-1"
                    )
                ], xs=12, md=4),

                dbc.Col([
                    html.Label("🎯 Tägliches Ziel (Reps)", style={"fontWeight": "bold"}),
                    dcc.Input(
                        id="target-reps",
                        type="number",
                        placeholder="z.B. 50",
                        className="form-control mt-1"
                    )
                ], xs=12, md=4),
            ]),

            dbc.Button("✅ Ziel speichern", id="add-target-btn", color="info", size="lg", className="mt-3 w-100", style={"fontWeight": "bold"}),
            html.Div(id="target-output", className="mt-3 text-success", style={"fontSize": "1.1rem", "fontWeight": "bold"}),
        ], style={"backgroundColor": "#2b3035"})
    ], className="mb-4 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"}),

    html.Div([
        html.Hr(style={"borderTop": "2px solid #E879F9", "marginTop": "40px", "marginBottom": "30px"}),
        html.H4("📋 Aktuelle Ziele", className="mb-4", style={"color": "#E879F9", "fontWeight": "bold"})
    ]),
    dbc.Card([
        dbc.CardBody([
            dash_table.DataTable(
                id="targets-table",
                columns=[
                    {"name": "Person", "id": "person"},
                    {"name": "Übung", "id": "exercise"},
                    {"name": "Tägliches Ziel", "id": "target_reps"},
                ],
                style_cell={
                    "textAlign": "left", 
                    "padding": "12px", 
                    "backgroundColor": "#2b3035", 
                    "color": "white",
                    "border": "1px solid #404040"
                },
                style_header={
                    "backgroundColor": "#1a1d20", 
                    "color": "#E879F9", 
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "border": "1px solid #404040"
                },
                style_table={"overflowX": "auto"},
                style_data_conditional=[
                    {"if": {"state": "selected"}, "backgroundColor": "#404040", "border": "2px solid #E879F9"},
                ],
                row_deletable=True,
                page_size=10
            )
        ], style={"backgroundColor": "#222629", "padding": "20px"})
    ], className="mb-4 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"}),
])


# -------------------------------------------------------------
# CALLBACKS
# -------------------------------------------------------------
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "tab-workouts":
        return workout_tab
    elif active_tab == "tab-targets":
        return targets_tab
    return html.Div("Wähle einen Tab")

@app.callback(
    Output("exercise", "options"),
    Input("interval", "n_intervals")
)
def update_exercise_options(_):
    exercises = get_all_exercises()
    options = [{"label": ex, "value": ex} for ex in exercises]
    return options

@app.callback(
    Output("target-exercise", "options"),
    Input("interval", "n_intervals")
)
def update_target_exercise_options(_):
    exercises = get_all_exercises()
    options = [{"label": ex, "value": ex} for ex in exercises]
    return options

@app.callback(
    Output("person", "options"),
    Input("interval", "n_intervals")
)
def update_person_options(_):
    people = get_all_people()
    options = [{"label": name, "value": name} for name in people]
    return options

@app.callback(
    Output("target-person", "options"),
    Input("interval", "n_intervals")
)
def update_target_person_options(_):
    people = get_all_people()
    options = [{"label": name, "value": name} for name in people]
    return options

@app.callback(
    Output("output", "children"),
    Input("add-btn", "n_clicks"),
    State("person", "value"),
    State("exercise", "value"),
    State("reps", "value"),
    State("date-picker", "date")
)
def add_set_callback(n, person, exercise, reps, date):
    if not n:
        return ""
    insert_set(person, exercise, reps, date)
    return f"Gespeichert: {person} – {exercise} – {reps} Wiederholungen"

@app.callback(
    Output("person-output", "children"),
    Input("add-person-btn", "n_clicks"),
    State("new-person-name", "value")
)
def add_person_callback(n, name):
    if not n:
        return ""
    if not name:
        return "Bitte Namen eingeben!"
    success = add_person(name)
    if success:
        return f"Person '{name}' erfolgreich hinzugefügt!"
    else:
        return f"Person '{name}' existiert bereits!"

@app.callback(
    Output("exercise-output", "children"),
    Input("add-exercise-btn", "n_clicks"),
    State("new-exercise-name", "value")
)
def add_exercise_callback(n, name):
    if not n:
        return ""
    if not name:
        return "Bitte Übungsname eingeben!"
    success = add_exercise(name)
    if success:
        return f"Übung '{name}' erfolgreich hinzugefügt!"
    else:
        return f"Übung '{name}' existiert bereits!"

@app.callback(
    Output("people-sections", "children"),
    Input("interval", "n_intervals")
)
def update_people_sections(_):
    people = get_all_people()
    sections = []
    
    for person in people:
        progress = get_today_progress(person)
        data = load_data(person)
        
        # Create progress section
        if progress:
            progress_charts = []
            for item in progress:
                chart = dbc.Col([
                    html.Div([
                        html.Div(
                            item['exercise'],
                            style={
                                "textAlign": "center",
                                "fontSize": "14px",
                                "fontWeight": "bold",
                                "color": "white",
                                "marginBottom": "10px"
                            }
                        ),
                        html.Div([
                            html.Div([
                                dcc.Graph(
                                    figure=create_progress_chart(
                                        item['exercise'], 
                                        item['actual'], 
                                        item['target'], 
                                        item['percentage']
                                    ),
                                    config={'displayModeBar': False},
                                    style={'margin': '0'}
                                )
                            ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
                            html.Div(
                                [html.Div("🎉", style={"fontSize": "32px", "marginBottom": "5px"}),
                                 html.Div("Good job!", style={"fontSize": "16px", "fontWeight": "bold"})],
                                style={
                                    "display": "inline-block",
                                    "verticalAlign": "middle",
                                    "marginLeft": "15px",
                                    "padding": "15px 20px",
                                    "backgroundColor": "rgba(40, 167, 69, 0.2)",
                                    "border": "2px solid #28a745",
                                    "borderRadius": "10px",
                                    "color": "#28a745",
                                    "textAlign": "center",
                                    "boxShadow": "0 0 15px rgba(40, 167, 69, 0.3)"
                                }
                            ) if item['percentage'] >= 100 else html.Div()
                        ], style={'textAlign': 'center', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
                        html.Div(
                            f"{item['actual']}/{item['target']} Reps",
                            style={
                                "textAlign": "center",
                                "fontSize": "14px",
                                "fontWeight": "bold",
                                "color": "#B794F6",
                                "marginTop": "5px"
                            }
                        )
                    ], style={'textAlign': 'center'})
                ], xs=12, sm=6, md=4, lg=3, className="mb-3")
                progress_charts.append(chart)
            progress_section = dbc.Row(progress_charts, className="mb-3")
        else:
            progress_section = html.Div("Keine Ziele gesetzt", style={"color": "#888", "fontStyle": "italic", "marginBottom": "20px"})
        
        # Create section for this person with distinctive styling
        section = dbc.Card([
            dbc.CardHeader([
                html.H3(person, className="mb-0", style={"color": "#E879F9", "fontWeight": "bold"})
            ], style={"backgroundColor": "#1e1e1e", "borderBottom": "3px solid #E879F9"}),
            dbc.CardBody([
                html.Div([
                    html.H5("📊 Heutige Fortschritte", className="mb-3", style={"color": "#adb5bd"}),
                    progress_section
                ], className="mb-4"),
                html.Div([
                    html.H5("📝 Workout-Verlauf", className="mb-3", style={"color": "#adb5bd"}),
                    dash_table.DataTable(
                        id={'type': 'person-table', 'person': person},
                        columns=[
                            {"name": "Datum", "id": "date"},
                            {"name": "Übungen", "id": "exercise"},
                            {"name": "Reps", "id": "repetitions"},
                        ],
                        data=data.to_dict("records") if not data.empty else [],
                        style_cell={
                            "textAlign": "left", 
                            "padding": "12px", 
                            "backgroundColor": "#2b3035", 
                            "color": "white",
                            "border": "1px solid #404040"
                        },
                        style_header={
                            "backgroundColor": "#1a1d20", 
                            "color": "#E879F9", 
                            "fontWeight": "bold",
                            "textAlign": "center",
                            "border": "1px solid #404040"
                        },
                        style_cell_conditional=[
                            {"if": {"column_id": "date"}, "textAlign": "center", "fontWeight": "bold"},
                        ],
                        style_table={"overflowX": "auto"},
                        style_data_conditional=[
                            {
                                "if": {"state": "selected"}, 
                                "backgroundColor": "#404040", 
                                "border": "2px solid #E879F9"
                            },
                        ],
                        row_deletable=True,
                        page_size=10
                    )
                ])
            ], style={"backgroundColor": "#222629"})
        ], className="mb-5 shadow-lg", style={"border": "2px solid #343a40", "borderRadius": "15px", "overflow": "hidden"})
        sections.append(section)
    
    return sections

@app.callback(
    Output({'type': 'person-table', 'person': dash.dependencies.MATCH}, 'data'),
    Input({'type': 'person-table', 'person': dash.dependencies.MATCH}, 'data_previous'),
    State({'type': 'person-table', 'person': dash.dependencies.MATCH}, 'data'),
    State({'type': 'person-table', 'person': dash.dependencies.MATCH}, 'id'),
    prevent_initial_call=True
)
def delete_row_from_table(previous, current, table_id):
    if previous is None or current is None:
        return current
    if len(previous) > len(current):
        deleted_ids = [row["id"] for row in previous if row not in current]
        for set_id in deleted_ids:
            delete_set(set_id)
    person = table_id['person']
    return load_data(person).to_dict("records")

@app.callback(
    Output("target-output", "children"),
    Input("add-target-btn", "n_clicks"),
    State("target-person", "value"),
    State("target-exercise", "value"),
    State("target-reps", "value")
)
def add_target_callback(n, person, exercise, target_reps):
    if not n:
        return ""
    if not person or not exercise or not target_reps:
        return "Bitte alle Felder ausfüllen!"
    insert_or_update_target(person, exercise, target_reps)
    return f"Ziel gespeichert: {person} – {exercise} – {target_reps} Reps pro Tag"

@app.callback(
    Output("targets-table", "data"),
    Input("interval", "n_intervals"),
    Input("add-target-btn", "n_clicks")
)
def update_targets_table(_, __):
    df = get_all_targets()
    return df.to_dict("records") if not df.empty else []

@app.callback(
    Output("targets-table", "data", allow_duplicate=True),
    Input("targets-table", "data_previous"),
    State("targets-table", "data"),
    prevent_initial_call=True
)
def delete_target_row(previous, current):
    if previous is None or current is None:
        return current
    if len(previous) > len(current):
        deleted_ids = [row["id"] for row in previous if row not in current]
        for target_id in deleted_ids:
            delete_target(target_id)
    df = get_all_targets()
    return df.to_dict("records") if not df.empty else []




if __name__ == "__main__":
    app.run(debug=False,  host="0.0.0.0", port=8050)
