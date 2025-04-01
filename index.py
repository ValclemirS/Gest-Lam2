"""
Dashboard de Gestão de Laminação a Frio - Versão Simplificada

Este dashboard exibe métricas operacionais de uma fábrica de laminação a frio, 
permitindo entrada manual de dados via formulário HTML e atualização em tempo real dos gráficos.
"""

from collections import defaultdict
import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
import os
import json

# Inicializa o app Dash com Bootstrap para design responsivo
server = Flask(__name__)
app = dash.Dash(
    __name__, 
    server=server,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

# Caminho para o arquivo de dados
DATA_FILE = 'dashboard_data.json'

# Funções para gerenciar os dados persistentes
def load_data():
    """Carrega os dados do arquivo JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    """Salva os dados no arquivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Carrega os dados iniciais
initial_data = load_data()

# Dados iniciais com tipos de dados explícitos (se o arquivo estiver vazio)
if not initial_data:
    INITIAL_DATA = {
        "Tipo": pd.Series(dtype='str'),
        "Valor": pd.Series(dtype='float'),
        "Turma/Semana": pd.Series(dtype='str')
    }
    initial_df = pd.DataFrame(INITIAL_DATA)
    initial_data = initial_df.to_dict('records')
    save_data(initial_data)

# Calculate KPIs
kpis = calculate_kpis(data)

# Color theme
colors = {
    'primary': '#1A5276',    # Azul escuro
    'secondary': '#2874A6',  # Azul médio
    'accent': '#3498DB',     # Azul claro
    'positive': '#27AE60',   # Verde
    'warning': '#F39C12',    # Amarelo/Laranja
    'negative': '#E74C3C',   # Vermelho
    'background': '#F5F5F5', # Cinza claro
    'text': '#2C3E50',       # Cinza escuro/azulado
    'white': '#FFFFFF'       # Branco
}

# Configurações comuns para os gráficos
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
    
    fig_relatos = go.Figure()
    if not relatos_data.empty:
        # Agrupa por turma e tipo
        grouped = relatos_data.groupby(['Turma', 'Tipo'])['Valor'].sum().unstack().fillna(0)
        
        fig_relatos.add_trace(go.Bar(
            x=grouped.index,
            y=grouped['Relatos Concluídos'],
            name='Relatos Concluídos',
            marker_color=colors['positive'],
            text=grouped['Relatos Concluídos'],
            textposition='auto',
        ))
        
        fig_relatos.add_trace(go.Bar(
            x=grouped.index,
            y=grouped['Relatos Abertos'],
            name='Relatos Abertos',
            marker_color=colors['warning'],
            text=grouped['Relatos Abertos'],
            textposition='auto',
        ))
    
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
        y=[kpis.get('acidentes_spt', 0), kpis.get('acidentes_cpt', 0)],
        marker_color=[colors['warning'], colors['negative']],
        width=0.6,
        text=[kpis.get('acidentes_spt', 0), kpis.get('acidentes_cpt', 0)],
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
        title_text='Sucata por Turma',
        xaxis_title='Quantidade',
        yaxis_title='Turma',
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
        title_text='Retrabalho por Turma',
        xaxis_title='Quantidade',
        yaxis_title='Turma',
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
        title_text='Produção Mensal',
        xaxis_title='Turma',
        yaxis_title='Quantidade (ton)',
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
        title_text='Horas Extras por Turma',
        xaxis_title='Turma',
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
        title_text='Treinamentos Pendentes por Turma',
        barmode='group',
        xaxis_title='Turma',
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
        title_text='Tempo de Interrupção por Turma',
        xaxis_title='Turma',
        yaxis_title='Horas',
        **layout_settings
    )
    
    return (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
            fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao)

def create_kpi_card(title, value, indicator=None, prefix="", suffix=""):
    """Cria um componente de cartão KPI para o dashboard."""
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

# Gera dados iniciais e gráficos
current_date = datetime.now()
current_week = current_date.isocalendar()[1]
start_of_week = current_date - timedelta(days=current_date.weekday())
end_of_week = start_of_week + timedelta(days=6)

# Gera gráficos iniciais
(fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
 fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao) = generate_graphs(initial_data)

# Cria o cabeçalho do dashboard
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

# Layout principal do dashboard
app.layout = dbc.Container([
    # Componente de intervalo para atualização automática
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # em milissegundos (5 segundos)
        n_intervals=0
    ),
    
    # Cabeçalho
    header,
    
    # Conteúdo principal do dashboard
    dbc.Row([
        # Primeira Coluna - Segurança
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("SEGURANÇA", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='relatos-chart',
                        figure=fig_relatos,
                        config=chart_config,
                        className="dashboard-chart"
                    ),
                    dcc.Graph(
                        id='acidentes-chart',
                        figure=fig_acidentes,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        # Segunda Coluna - Qualidade
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("QUALIDADE", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='sucata-chart',
                        figure=fig_sucata,
                        config=chart_config,
                        className="dashboard-chart"
                    ),
                    dcc.Graph(
                        id='retrabalho-chart',
                        figure=fig_retrabalho,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        # Terceira Coluna - Produção
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PRODUÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='producao-chart',
                        figure=fig_producao,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ], className="mb-4"),
    
    # Segunda linha do dashboard
    dbc.Row([
        # Primeira Coluna - Pessoas
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PESSOAS", className="section-header")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(
                                id='horas-extras-chart',
                                figure=fig_horas_extras,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                id='treinamentos-chart',
                                figure=fig_treinamentos,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                id='faltas-chart',
                                figure=fig_faltas,
                                config=chart_config,
                                className="dashboard-chart"
                            )
                        ], md=4, sm=12)
                    ])
                ])
            ], className="dashboard-card")
        ], lg=8, md=12, sm=12),
        
        # Segunda Coluna - Interrupção
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("INTERRUPÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='interrupcao-chart',
                        figure=fig_interrupcao,
                        config=chart_config,
                        className="dashboard-chart"
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ]),
    
    # Rodapé
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Dashboard atualizado em " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"), className="footer-text"),
                html.P("© 2025 - Gestão Laminação a Frio", className="footer-text"),
                html.A("Acessar Formulário de Entrada", href="/form", className="btn btn-primary", style={'margin-top': '10px'})
            ], className="footer")
        ], width=12)
    ])
], fluid=True, className="dashboard-container")

# Define callbacks
@app.callback(
    [Output('relatos-chart', 'figure'),
     Output('acidentes-chart', 'figure'),
     Output('sucata-chart', 'figure'),
     Output('retrabalho-chart', 'figure'),
     Output('producao-chart', 'figure'),
     Output('horas-extras-chart', 'figure'),
     Output('treinamentos-chart', 'figure'),
     Output('faltas-chart', 'figure'),
     Output('interrupcao-chart', 'figure'),
     Output('dashboard-title', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_data(n_clicks):
    # Placeholder for refresh functionality
    # In a real app, you would reload the data here
    return [html.H3("GESTÃO LAMINAÇÃO A FRIO", id="dashboard-title")]

# Executa o aplicativo
if __name__ == '__main__':
    app.run(debug=True)