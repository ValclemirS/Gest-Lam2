import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

# Load data
data = pd.read_csv('train.csv')

# Initialize Dash app with Bootstrap for responsive design
app = dash.Dash(
    __name__, 
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
server = app.server

# Calculate KPIs
def calculate_kpis(data):
    kpis = {}
    
    # Safety KPIs
    kpis['relatos_abertos'] = data[data['Tipo'] == 'Relatos Abertos']['Valor'].values[0]
    kpis['relatos_concluidos'] = data[data['Tipo'] == 'Relatos Concluídos']['Valor'].values[0]
    kpis['completion_rate'] = round((kpis['relatos_concluidos'] / (kpis['relatos_abertos'] + kpis['relatos_concluidos'])) * 100, 1)
    
    kpis['acidentes_spt'] = data[data['Tipo'] == 'Acidentes SPT']['Valor'].values[0]
    kpis['acidentes_cpt'] = data[data['Tipo'] == 'Acidentes CPT']['Valor'].values[0]
    kpis['total_acidentes'] = kpis['acidentes_spt'] + kpis['acidentes_cpt']
    
    # Get last week's production
    producao_data = data[data['Tipo'] == 'Produção']
    kpis['producao_atual'] = producao_data['Valor'].iloc[-1] if not producao_data.empty else 0
    
    # Last 4 weeks trend for production
    if len(producao_data) >= 2:
        kpis['producao_trend'] = producao_data['Valor'].iloc[-1] - producao_data['Valor'].iloc[-2]
    else:
        kpis['producao_trend'] = 0
    
    # Quality KPIs
    sucata_data = data[data['Tipo'] == 'Sucata']
    kpis['sucata_total'] = sucata_data['Valor'].sum() if not sucata_data.empty else 0
    
    retrabalho_data = data[data['Tipo'] == 'Retrabalho']
    kpis['retrabalho_total'] = retrabalho_data['Valor'].sum() if not retrabalho_data.empty else 0
    
    # People KPIs
    horas_extras = data[data['Tipo'] == 'Horas Extras']
    kpis['horas_extras_total'] = horas_extras['Valor'].sum() if not horas_extras.empty else 0
    
    return kpis

# Generate current date information
current_date = datetime.now()
current_week = current_date.isocalendar()[1]
start_of_week = current_date - timedelta(days=current_date.weekday())
end_of_week = start_of_week + timedelta(days=6)

# Calculate KPIs
kpis = calculate_kpis(data)

# Color theme
colors = {
    'primary': '#1A5276',    # Dark blue
    'secondary': '#2874A6',  # Medium blue
    'accent': '#3498DB',     # Light blue
    'positive': '#27AE60',   # Green
    'warning': '#F39C12',    # Yellow/Orange
    'negative': '#E74C3C',   # Red
    'background': '#F5F5F5', # Light grey
    'text': '#2C3E50',       # Dark grey/blue
    'white': '#FFFFFF'       # White
}

# Common chart settings for consistency
chart_config = {
    'displayModeBar': False,
    'responsive': True
}

layout_settings = {
    'plot_bgcolor': colors['background'],
    'paper_bgcolor': colors['background'],
    'font': {
        'family': 'Arial, sans-serif',
        'color': colors['text'],
        'size': 12
    },
    'title': {
        'font': {
            'size': 16,
            'color': colors['text'],
            'family': 'Arial, sans-serif',
            'weight': 'bold'
        },
        'x': 0.5,
        'xanchor': 'center'
    },
    'margin': {'l': 40, 'r': 20, 't': 40, 'b': 40},
    'legend': {
        'orientation': 'h',
        'yanchor': 'bottom',
        'y': -0.3,
        'xanchor': 'center',
        'x': 0.5,
        'font': {'size': 10}
    },
    'xaxis': {
        'gridcolor': '#E0E0E0',
        'showgrid': True
    },
    'yaxis': {
        'gridcolor': '#E0E0E0',
        'showgrid': True
    }
}

# Função para gerar os gráficos com fontes e elementos maiores
def generate_graphs(data):
    # SEGURANÇA
    # Relatos chart (donut chart for better visualization)
    labels = ['Relatos Concluídos', 'Relatos Abertos']
    values = [kpis['relatos_concluidos'], kpis['relatos_abertos']]
    
    fig_relatos = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.7,
        marker_colors=[colors['positive'], colors['warning']]
    )])
    
    fig_relatos.update_layout(
    title_text='Status dos Relatos',
    annotations=[{
        'text': f"{kpis['completion_rate']}%<br>Concluídos",
        'x': 0.5,
        'y': 0.5,
        'font_size': 16,
        'showarrow': False
    }],
    **layout_settings
)

    # Acidentes chart with improved visualization
    fig_acidentes = go.Figure()
    
    fig_acidentes.add_trace(go.Bar(
        x=['SPT', 'CPT'],
        y=[kpis['acidentes_spt'], kpis['acidentes_cpt']],
        marker_color=[colors['warning'], colors['negative']],
        width=0.6,
        text=[kpis['acidentes_spt'], kpis['acidentes_cpt']],
        textposition='auto',
    ))
    
    fig_acidentes.update_layout(
    title_text='Acidentes',
    annotations=[{
        'text': f"Total: {kpis['total_acidentes']}",
        'x': 0.5,
        'y': 0.9,
        'showarrow': False,
        'font': {'size': 12}
    }],
    **layout_settings
)

    # QUALIDADE
    # Sucata data visualization with improved appearance
    sucata_data = data[data['Tipo'] == 'Sucata']
    
    fig_sucata = go.Figure()
    fig_sucata.add_trace(go.Bar(
        y=sucata_data['Turma/Semana'],
        x=sucata_data['Valor'],
        orientation='h',
        marker_color=colors['accent'],
        text=sucata_data['Valor'],
        textposition='auto',
    ))
    
    fig_sucata.update_layout(
        title_text='Sucata por Equipe/Semana',
        xaxis_title='Quantidade',
        yaxis_title='Equipe/Semana',
        **layout_settings
    )

    # Retrabalho data with enhanced colors
    retrabalho_data = data[data['Tipo'] == 'Retrabalho']
    
    fig_retrabalho = go.Figure()
    fig_retrabalho.add_trace(go.Bar(
        y=retrabalho_data['Turma/Semana'],
        x=retrabalho_data['Valor'],
        orientation='h',
        marker_color=colors['warning'],
        text=retrabalho_data['Valor'],
        textposition='auto',
    ))
    
    fig_retrabalho.update_layout(
        title_text='Retrabalho por Equipe/Semana',
        xaxis_title='Quantidade',
        yaxis_title='Equipe/Semana',
        **layout_settings
    )

    # PRODUÇÃO
    # Production chart with trend line
    producao_data = data[data['Tipo'] == 'Produção']
    
    fig_producao = go.Figure()
    
    fig_producao.add_trace(go.Bar(
        x=producao_data['Turma/Semana'],
        y=producao_data['Valor'],
        marker_color=colors['primary'],
        width=0.5,
        name='Produção',
        text=producao_data['Valor'],
        textposition='auto',
    ))
    
    # Add target line (as an example - replace with actual target)
    target = producao_data['Valor'].mean() * 1.1
    
    fig_producao.add_trace(go.Scatter(
        x=producao_data['Turma/Semana'],
        y=[target] * len(producao_data),
        mode='lines',
        name='Meta',
        line=dict(color=colors['negative'], width=2, dash='dash'),
    ))
    
    fig_producao.update_layout(
        title_text='Produção Semanal',
        xaxis_title='Equipe/Semana',
        yaxis_title='Quantidade',
        **layout_settings
    )

    # PESSOAS
    # Enhanced horas extras visualization
    horas_extras_data = data[data['Tipo'] == 'Horas Extras']
    
    fig_horas_extras = go.Figure()
    fig_horas_extras.add_trace(go.Bar(
        x=horas_extras_data['Turma/Semana'],
        y=horas_extras_data['Valor'],
        marker_color=colors['secondary'],
        width=0.6,
        text=horas_extras_data['Valor'],
        textposition='auto',
    ))
    
    fig_horas_extras.update_layout(
        title_text='Horas Extras por Equipe/Semana',
        xaxis_title='Equipe/Semana',
        yaxis_title='Horas',
        **layout_settings
    )

    # Improved treinamentos visualization with better legend
    treinamentos_data = data[data['Tipo'].str.contains('Treinamento')]
    
    fig_treinamentos = go.Figure()
    
    # Filter data for each training type
    obrigatorios = treinamentos_data[treinamentos_data['Tipo'] == 'Treinamento Obrigatório']
    eletivos = treinamentos_data[treinamentos_data['Tipo'] == 'Treinamento Eletivo']
    
    fig_treinamentos.add_trace(go.Bar(
        x=obrigatorios['Turma/Semana'],
        y=obrigatorios['Valor'],
        name='Obrigatórios',
        marker_color=colors['negative'],
        text=obrigatorios['Valor'],
        textposition='auto',
    ))
    
    fig_treinamentos.add_trace(go.Bar(
        x=eletivos['Turma/Semana'],
        y=eletivos['Valor'],
        name='Eletivos',
        marker_color=colors['accent'],
        text=eletivos['Valor'],
        textposition='auto',
    ))
    
    fig_treinamentos.update_layout(
        title_text='Treinamentos Pendentes',
        barmode='group',
        xaxis_title='Equipe/Semana',
        yaxis_title='Quantidade',
        **layout_settings
    )

    # Faltas - assuming we might get data later
    fig_faltas = go.Figure()
    
    # Sample data - replace with actual data when available
    sample_weeks = ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4']
    sample_faltas = [2, 1, 3, 0]
    
    fig_faltas.add_trace(go.Bar(
        x=sample_weeks,
        y=sample_faltas,
        marker_color=colors['warning'],
        text=sample_faltas,
        textposition='auto',
    ))
    
    fig_faltas.update_layout(
        title_text='Faltas por Semana (Dados Exemplo)',
        xaxis_title='Semana',
        yaxis_title='Quantidade',
        **layout_settings
    )

    # INTERRUPÇÃO
    # Enhanced line chart
    interrupcao_data = data[data['Tipo'] == 'Interrupção']
    
    fig_interrupcao = go.Figure()
    
    fig_interrupcao.add_trace(go.Scatter(
        x=interrupcao_data['Turma/Semana'],
        y=interrupcao_data['Valor'],
        mode='lines+markers',
        line=dict(color=colors['negative'], width=3),
        marker=dict(size=10, color=colors['negative']),
        fill='tozeroy',
        fillcolor=f'rgba({int(colors["negative"][1:3], 16)}, {int(colors["negative"][3:5], 16)}, {int(colors["negative"][5:7], 16)}, 0.2)',
    ))
    
    fig_interrupcao.update_layout(
        title_text='Tempo de Interrupção por Semana',
        xaxis_title='Semana',
        yaxis_title='Horas',
        **layout_settings
    )

    return (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
            fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao)

# Generate graphs
(fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
 fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao) = generate_graphs(data)

# Create KPI card component
def create_kpi_card(title, value, indicator=None, prefix="", suffix=""):
    indicator_color = colors['white']
    indicator_icon = ""
    
    if indicator == "up":
        indicator_color = colors['positive']
        indicator_icon = "↑"
    elif indicator == "down":
        indicator_color = colors['negative']
        indicator_icon = "↓"
        
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H4(title, className="card-title"),
                    html.Div([
                        html.Span(f"{prefix}{value}{suffix}", className="kpi-value"),
                        html.Span(indicator_icon, className="indicator", style={"color": indicator_color})
                    ], className="kpi-container")
                ]
            )
        ],
        className="kpi-card"
    )

# Dashboard Header
header = dbc.Container([
    dbc.Row([
        dbc.Col(html.Img(src="/assets/logo.png", height="60px"), width=2),
        dbc.Col(html.H3("GESTÃO LAMINAÇÃO A FRIO", id="dashboard-title"), width=8),
        dbc.Col([
            html.Div([
                html.Span(f"Semana {current_week}"),
                html.Br(),
                html.Span(f"{start_of_week.strftime('%d/%m')} - {end_of_week.strftime('%d/%m/%Y')}")
            ], className="date-display")
        ], width=2)
    ], className="header-row"),
    
    # KPI Summary Row
    dbc.Row([
        dbc.Col(create_kpi_card("Relatos Concluídos", f"{kpis['completion_rate']}%", "up"), width=3),
        dbc.Col(create_kpi_card("Acidentes Totais", kpis['total_acidentes'], "down"), width=3),
        dbc.Col(create_kpi_card("Produção Atual", kpis['producao_atual'], 
                               "up" if kpis['producao_trend'] > 0 else "down" if kpis['producao_trend'] < 0 else None,
                               suffix=" ton"), width=3),
        dbc.Col(create_kpi_card("Horas Extras", kpis['horas_extras_total'], "down", suffix="h"), width=3),
    ], className="kpi-row"),
    
    html.Hr(className="my-4")
], fluid=True, className="dashboard-header")

# Dashboard Layout
app.layout = dbc.Container([
    header,
    
    # Filters Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Filtros", className="card-title"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Período:"),
                            dcc.Dropdown(
                                id='period-filter',
                                options=[
                                    {'label': 'Última Semana', 'value': 'week'},
                                    {'label': 'Último Mês', 'value': 'month'},
                                    {'label': 'Último Trimestre', 'value': 'quarter'},
                                ],
                                value='week',
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Turma:"),
                            dcc.Dropdown(
                                id='team-filter',
                                options=[
                                    {'label': 'Todas', 'value': 'all'},
                                    {'label': 'Turma A', 'value': 'A'},
                                    {'label': 'Turma B', 'value': 'B'},
                                    {'label': 'Turma C', 'value': 'C'},
                                ],
                                value='all',
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Atualizar:"),
                            html.Button(
                                "Atualizar Dados", 
                                id="refresh-btn", 
                                className="btn btn-primary"
                            )
                        ], width=4),
                    ])
                ])
            ], className="filter-card")
        ], width=12)
    ], className="mb-4"),
    
    # Main Dashboard Content
    dbc.Row([
        # First Column - Security
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("SEGURANÇA", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        figure=fig_relatos,
                        config=chart_config,
                        className="dashboard-chart"
                    ),
                    dcc.Graph(
                        figure=fig_acidentes,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        # Second Column - Quality
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("QUALIDADE", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        figure=fig_sucata,
                        config=chart_config,
                        className="dashboard-chart"
                    ),
                    dcc.Graph(
                        figure=fig_retrabalho,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        # Third Column - Production
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PRODUÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        figure=fig_producao,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ], className="mb-4"),
    
    # Second Row of Dashboard Content
    dbc.Row([
        # First Column - People
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PESSOAS", className="section-header")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(
                                figure=fig_horas_extras,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                figure=fig_treinamentos,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                figure=fig_faltas,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12)
                    ])
                ])
            ], className="dashboard-card")
        ], lg=8, md=12, sm=12),
        
        # Second Column - Interruption
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("INTERRUPÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        figure=fig_interrupcao,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ]),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Dashboard atualizado em " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"), className="footer-text"),
                html.P("© 2025 - Gestão Laminação a Frio", className="footer-text")
            ], className="footer")
        ], width=12)
    ])
], fluid=True, className="dashboard-container")

# Define callbacks
@app.callback(
    [Output("header", "children")],
    [Input("refresh-btn", "n_clicks")]
)
def update_data(n_clicks):
    # Placeholder for refresh functionality
    # In a real app, you would reload the data here
    return [html.H3("GESTÃO LAMINAÇÃO A FRIO", id="dashboard-title")]

# Run app
if __name__ == '__main__':
    app.run(debug=True)