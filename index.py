"""
Dashboard de Gestão de Laminação a Frio - Versão Simplificada
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

server = Flask(__name__)
app = dash.Dash(
    __name__, 
    server=server,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

# Configurações para TV 55" com scroll
app.layout = html.Div(style={
    'width': '1920px',
    'min-height': '1080px',
    'margin': '0 auto',
    'padding': '10px',
    'overflow-y': 'auto',
    'overflow-x': 'hidden'
})

DATA_FILE = 'dashboard_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

initial_data = load_data()

if not initial_data:
    INITIAL_DATA = {
        "Tipo": pd.Series(dtype='str'),
        "Valor": pd.Series(dtype='float'),
        "Turma": pd.Series(dtype='str')
    }
    initial_df = pd.DataFrame(INITIAL_DATA)
    initial_data = initial_df.to_dict('records')
    save_data(initial_data)

colors = {
    'primary': '#1A5276',
    'secondary': '#2874A6',
    'accent': '#3498DB',
    'positive': '#27AE60',
    'warning': '#F39C12',
    'negative': '#E74C3C',
    'background': '#F5F5F5',
    'text': '#2C3E50',
    'white': '#FFFFFF'
}

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

def calculate_kpis(data):
    kpis = defaultdict(int)
    
    if isinstance(data, list):
        data = pd.DataFrame(data)
    
    if data.empty:
        return kpis
    
    try:
        relatos_abertos = data[data['Tipo'] == 'Relatos Abertos']['Valor'].sum()
        relatos_concluidos = data[data['Tipo'] == 'Relatos Concluídos']['Valor'].sum()
        
        kpis['relatos_abertos'] = relatos_abertos
        kpis['relatos_concluidos'] = relatos_concluidos
        total = relatos_abertos + relatos_concluidos
        kpis['completion_rate'] = round((relatos_concluidos / total) * 100, 1) if total > 0 else 0
    except:
        pass
    
    try:
        kpis['acidentes_spt'] = data[data['Tipo'] == 'Acidentes SPT']['Valor'].sum()
        kpis['acidentes_cpt'] = data[data['Tipo'] == 'Acidentes CPT']['Valor'].sum()
        kpis['total_acidentes'] = kpis['acidentes_spt'] + kpis['acidentes_cpt']
    except:
        pass
    
    try:
        producao_data = data[data['Tipo'] == 'Produção']
        kpis['producao_atual'] = producao_data['Valor'].iloc[-1] if not producao_data.empty else 0
        
        if len(producao_data) >= 2:
            kpis['producao_trend'] = producao_data['Valor'].iloc[-1] - producao_data['Valor'].iloc[-2]
        else:
            kpis['producao_trend'] = 0
    except:
        pass
    
    try:
        kpis['sucata_total'] = data[data['Tipo'] == 'Sucata']['Valor'].sum()
        kpis['retrabalho_total'] = data[data['Tipo'] == 'Retrabalho']['Valor'].sum()
    except:
        pass
    
    try:
        kpis['horas_extras_total'] = data[data['Tipo'] == 'Horas Extras']['Valor'].sum()
    except:
        pass
    
    return kpis

def generate_graphs(data):
    kpis = calculate_kpis(data)
    
    if isinstance(data, list):
        data = pd.DataFrame(data)
    
    # 1. Gráfico de Relatos (Barras verticais)
    fig_relatos = go.Figure()
    
    if not data.empty:
        turmas = data['Turma'].unique()
        
        for turma in turmas:
            turma_data = data[data['Turma'] == turma]
            relatos_abertos = turma_data[turma_data['Tipo'] == 'Relatos Abertos']['Valor'].sum()
            relatos_concluidos = turma_data[turma_data['Tipo'] == 'Relatos Concluídos']['Valor'].sum()
            
            fig_relatos.add_trace(go.Bar(
                x=[turma],
                y=[relatos_concluidos],
                name='Concluídos',
                marker_color=colors['positive']
            ))
            
            fig_relatos.add_trace(go.Bar(
                x=[turma],
                y=[relatos_abertos],
                name='Abertos',
                marker_color=colors['warning']
            ))
    
    fig_relatos.update_layout(
        title_text='Relatos por Turma',
        barmode='stack',
        xaxis_title='Turma',
        yaxis_title='Quantidade',
        **layout_settings
    )
    
    # 2. Gráfico de Acidentes
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
            'text': f"Total: {kpis.get('total_acidentes', 0)}",
            'x': 0.5,
            'y': 0.9,
            'showarrow': False,
            'font': {'size': 12}
        }],
        **layout_settings
    )
    
    # 3. Gráfico de Sucata
    sucata_data = data[data['Tipo'] == 'Sucata'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])
    
    fig_sucata = go.Figure()
    if not sucata_data.empty:
        fig_sucata.add_trace(go.Bar(
            y=sucata_data['Turma'],
            x=sucata_data['Valor'],
            orientation='h',
            marker_color=colors['positive'],
            text=sucata_data['Valor'],
            textposition='auto',
        ))
    
    fig_sucata.update_layout(
        title_text='Sucata por Turma',
        xaxis_title='Quantidade',
        yaxis_title='Turma',
        **layout_settings
    )
    
    # 4. Gráfico de Retrabalho
    retrabalho_data = data[data['Tipo'] == 'Retrabalho'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])
    
    fig_retrabalho = go.Figure()
    if not retrabalho_data.empty:
        fig_retrabalho.add_trace(go.Bar(
            y=retrabalho_data['Turma'],
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
    
    # 5. Gráfico de Produção
    producao_data = data[data['Tipo'] == 'Produção'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])
    
    fig_producao = go.Figure()
    if not producao_data.empty:
        fig_producao.add_trace(go.Bar(
            x=producao_data['Turma'],
            y=producao_data['Valor'],
            marker_color=colors['primary'],
            width=0.5,
            name='Produção',
            text=producao_data['Valor'],
            textposition='auto',
        ))
        
        target = producao_data['Valor'].mean() * 1.1
        fig_producao.add_trace(go.Scatter(
            x=producao_data['Turma'],
            y=[target] * len(producao_data),
            mode='lines',
            name='Meta',
            line=dict(color=colors['negative'], width=2, dash='dash'),
        ))
    
    fig_producao.update_layout(
        title_text='Produção Mensal',
        xaxis_title='Turma',
        yaxis_title='Quantidade',
        **layout_settings
    )
    
    # 6. Gráfico de Horas Extras
    horas_extras_data = data[data['Tipo'] == 'Horas Extras'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])
    
    fig_horas_extras = go.Figure()
    if not horas_extras_data.empty:
        fig_horas_extras.add_trace(go.Bar(
            x=horas_extras_data['Turma'],
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
    
    # 7. Gráfico de Treinamentos
    fig_treinamentos = go.Figure()
    
    if not data.empty and 'Tipo' in data.columns:
        obrigatorios = data[data['Tipo'] == 'Treinamento Obrigatório'] if not data.empty else pd.DataFrame()
        eletivos = data[data['Tipo'] == 'Treinamento Eletivo'] if not data.empty else pd.DataFrame()
        
        if not obrigatorios.empty:
            fig_treinamentos.add_trace(go.Bar(
                x=obrigatorios['Turma'],
                y=obrigatorios['Valor'],
                name='Obrigatórios',
                marker_color=colors['negative'],
                text=obrigatorios['Valor'],
                textposition='auto',
            ))
        
        if not eletivos.empty:
            fig_treinamentos.add_trace(go.Bar(
                x=eletivos['Turma'],
                y=eletivos['Valor'],
                name='Eletivos',
                marker_color=colors['accent'],
                text=eletivos['Valor'],
                textposition='auto',
            ))
    
    fig_treinamentos.update_layout(
        title_text='Treinamentos Pendentes',
        barmode='group',
        xaxis_title='Turma',
        yaxis_title='Quantidade',
        **layout_settings
    )
    
    # 8. Gráfico de Faltas
    faltas_data = data[data['Tipo'] == 'Faltas'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])

    fig_faltas = go.Figure()
    if not faltas_data.empty:
        fig_faltas.add_trace(go.Bar(
            x=faltas_data['Turma'],
            y=faltas_data['Valor'],
            marker_color=colors['warning'],
            text=faltas_data['Valor'],
            textposition='auto',
        ))

    fig_faltas.update_layout(
        title_text='Faltas por Turma',
        xaxis_title='Turma',
        yaxis_title='Quantidade',
        **layout_settings
    )
    
    # 9. Gráfico de Interrupção
    interrupcao_data = data[data['Tipo'] == 'Interrupção'] if not data.empty else pd.DataFrame(columns=['Turma', 'Valor'])
    
    fig_interrupcao = go.Figure()
    if not interrupcao_data.empty:
        fig_interrupcao.add_trace(go.Scatter(
            x=interrupcao_data['Turma'],
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

current_date = datetime.now()
current_month = current_date.month
month_name = current_date.strftime("%B")

header = dbc.Container([
    dbc.Row([
        dbc.Col(html.Img(src="/assets/logo.png", height="60px"), width=2),
        dbc.Col(html.H3("GESTÃO LAMINAÇÃO A FRIO", id="dashboard-title"), width=8),
        dbc.Col([
            html.Div([
                html.Span(f"Mês: {month_name}"),
                html.Br(),
                html.Span(current_date.strftime('%d/%m/%Y'))
            ], className="date-display")
        ], width=2)
    ], className="header-row"),
    
    dbc.Row([
        dbc.Col(create_kpi_card("Relatos Concluídos", f"{calculate_kpis(initial_data).get('completion_rate', 0)}%", "up"), width=3),
        dbc.Col(create_kpi_card("Acidentes Totais", calculate_kpis(initial_data).get('total_acidentes', 0), "down"), width=3),
        dbc.Col(create_kpi_card("Produção Atual", calculate_kpis(initial_data).get('producao_atual', 0), 
               "up" if calculate_kpis(initial_data).get('producao_trend', 0) > 0 else "down" if calculate_kpis(initial_data).get('producao_trend', 0) < 0 else None,
               suffix=" ton"), width=3),
        dbc.Col(create_kpi_card("Horas Extras", calculate_kpis(initial_data).get('horas_extras_total', 0), "down", suffix="h"), width=3),
    ], className="kpi-row"),
    
    html.Hr(className="my-4")
], fluid=True, className="dashboard-header")

app.layout = dbc.Container([
    dcc.Interval(
        id='interval-component',
        interval=5*1000,
        n_intervals=0
    ),
    
    header,
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("SEGURANÇA", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='relatos-chart',
                        figure=generate_graphs(initial_data)[0],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    ),
                    dcc.Graph(
                        id='acidentes-chart',
                        figure=generate_graphs(initial_data)[1],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("QUALIDADE", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='sucata-chart',
                        figure=generate_graphs(initial_data)[2],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    ),
                    dcc.Graph(
                        id='retrabalho-chart',
                        figure=generate_graphs(initial_data)[3],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=6, sm=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PRODUÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='producao-chart',
                        figure=generate_graphs(initial_data)[4],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PESSOAS", className="section-header")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(
                                id='horas-extras-chart',
                                figure=generate_graphs(initial_data)[5],
                                config=chart_config,
                                className="dashboard-chart",
                                style={'height': '300px'}
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                id='treinamentos-chart',
                                figure=generate_graphs(initial_data)[6],
                                config=chart_config,
                                className="dashboard-chart",
                                style={'height': '300px'}
                            )
                        ], md=4, sm=12),
                        dbc.Col([
                            dcc.Graph(
                                id='faltas-chart',
                                figure=generate_graphs(initial_data)[7],
                                config=chart_config,
                                className="dashboard-chart",
                                style={'height': '300px'}
                            )
                        ], md=4, sm=12)
                    ])
                ])
            ], className="dashboard-card")
        ], lg=8, md=12, sm=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("INTERRUPÇÃO", className="section-header")),
                dbc.CardBody([
                    dcc.Graph(
                        id='interrupcao-chart',
                        figure=generate_graphs(initial_data)[8],
                        config=chart_config,
                        className="dashboard-chart",
                        style={'height': '400px'}
                    )
                ])
            ], className="dashboard-card")
        ], lg=4, md=12, sm=12),
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Dashboard atualizado em " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"), className="footer-text"),
                html.P("© 2025 - Gestão Laminação a Frio", className="footer-text"),
                html.A("Acessar Formulário de Entrada", href="/form", className="btn btn-primary", style={'margin-top': '10px'})
            ], className="footer")
        ], width=12)
    ])
], fluid=True, className="dashboard-container", style={
    'width': '1920px',
    'min-height': '1080px',
    'overflow-y': 'auto',
    'overflow-x': 'hidden',
    'margin': '0 auto',
    'padding': '10px'
})

@app.server.route('/form')
def serve_form():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'form.html')

@app.server.route('/api/add_data', methods=['POST'])
def add_data():
    try:
        new_data = request.json
        
        if not all(key in new_data for key in ['Turma']):
            return jsonify({'error': 'Dados incompletos - Turma é obrigatória'}), 400
            
        current_data = load_data()
        
        turma = new_data['Turma']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        indicators = {
            'Relatos Abertos': new_data.get('Relatos Abertos', 0),
            'Relatos Concluídos': new_data.get('Relatos Concluídos', 0),
            'Acidentes SPT': new_data.get('Acidentes SPT', 0),
            'Acidentes CPT': new_data.get('Acidentes CPT', 0),
            'Produção': new_data.get('Produção', 0),
            'Sucata': new_data.get('Sucata', 0),
            'Retrabalho': new_data.get('Retrabalho', 0),
            'Horas Extras': new_data.get('Horas Extras', 0),
            'Treinamento Obrigatório': new_data.get('Treinamento Obrigatório', 0),
            'Treinamento Eletivo': new_data.get('Treinamento Eletivo', 0),
            'Interrupção': new_data.get('Interrupção', 0),
            'Faltas': new_data.get('Faltas', 0)
        }
        
        for tipo, valor in indicators.items():
            if valor != 0:
                record = {
                    'Turma': turma,
                    'Tipo': tipo,
                    'Valor': float(valor),
                    'Timestamp': timestamp
                }
                current_data.append(record)
        
        save_data(current_data)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.server.route('/api/clear_data', methods=['POST'])
def clear_data():
    try:
        save_data([])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
def update_all_charts(n_intervals):
    data = load_data()
    df = pd.DataFrame(data)
    
    (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
     fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao) = generate_graphs(df)
    
    title = f"GESTÃO LAMINAÇÃO A FRIO (Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')})"
    
    return (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
            fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao, title)

if __name__ == '__main__':
    app.run(debug=True)