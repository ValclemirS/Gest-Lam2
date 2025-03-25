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

# Paleta de cores para o dashboard
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

def calculate_kpis(data):
    """Calcula os KPIs com base nos dados fornecidos."""
    kpis = defaultdict(int)
    
    # Converte para DataFrame se for uma lista de dicionários
    if isinstance(data, list):
        data = pd.DataFrame(data)
    
    # Verifica se há dados
    if data.empty:
        return kpis
    
    # KPIs de Segurança
    try:
        relatos_abertos = data[data['Tipo'] == 'Relatos Abertos']['Valor'].sum()
        relatos_concluidos = data[data['Tipo'] == 'Relatos Concluídos']['Valor'].sum()
        
        kpis['relatos_abertos'] = relatos_abertos
        kpis['relatos_concluidos'] = relatos_concluidos
        total = relatos_abertos + relatos_concluidos
        kpis['completion_rate'] = round((relatos_concluidos / total) * 100, 1) if total > 0 else 0
    except:
        pass
    
    # KPIs de Acidentes
    try:
        kpis['acidentes_spt'] = data[data['Tipo'] == 'Acidentes SPT']['Valor'].sum()
        kpis['acidentes_cpt'] = data[data['Tipo'] == 'Acidentes CPT']['Valor'].sum()
        kpis['total_acidentes'] = kpis['acidentes_spt'] + kpis['acidentes_cpt']
    except:
        pass
    
    # KPIs de Produção
    try:
        producao_data = data[data['Tipo'] == 'Produção']
        kpis['producao_atual'] = producao_data['Valor'].iloc[-1] if not producao_data.empty else 0
        
        if len(producao_data) >= 2:
            kpis['producao_trend'] = producao_data['Valor'].iloc[-1] - producao_data['Valor'].iloc[-2]
        else:
            kpis['producao_trend'] = 0
    except:
        pass
    
    # KPIs de Qualidade
    try:
        kpis['sucata_total'] = data[data['Tipo'] == 'Sucata']['Valor'].sum()
        kpis['retrabalho_total'] = data[data['Tipo'] == 'Retrabalho']['Valor'].sum()
    except:
        pass
    
    # KPIs de Pessoas
    try:
        kpis['horas_extras_total'] = data[data['Tipo'] == 'Horas Extras']['Valor'].sum()
    except:
        pass
    
    return kpis

def generate_graphs(data):
    """Gera todos os gráficos do dashboard com base nos dados fornecidos."""
    # Calcula os KPIs primeiro
    kpis = calculate_kpis(data)
    
    # Converte para DataFrame se for uma lista de dicionários
    if isinstance(data, list):
        data = pd.DataFrame(data)
    
    # 1. Gráfico de Relatos (Segurança)
    labels = ['Relatos Concluídos', 'Relatos Abertos']
    values = [kpis.get('relatos_concluidos', 0), kpis.get('relatos_abertos', 0)]
    
    fig_relatos = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.7,
        marker_colors=[colors['positive'], colors['warning']]
    )])
    
    fig_relatos.update_layout(
        title_text='Status dos Relatos',
        annotations=[{
            'text': f"{kpis.get('completion_rate', 0)}%<br>Concluídos",
            'x': 0.5,
            'y': 0.5,
            'font_size': 16,
            'showarrow': False
        }],
        **layout_settings
    )
    
    # 2. Gráfico de Acidentes (Segurança)
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
    
    # 3. Gráfico de Sucata (Qualidade)
    sucata_data = data[data['Tipo'] == 'Sucata'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])
    
    fig_sucata = go.Figure()
    if not sucata_data.empty:
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
    
    # 4. Gráfico de Retrabalho (Qualidade)
    retrabalho_data = data[data['Tipo'] == 'Retrabalho'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])
    
    fig_retrabalho = go.Figure()
    if not retrabalho_data.empty:
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
    
    # 5. Gráfico de Produção
    producao_data = data[data['Tipo'] == 'Produção'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])
    
    fig_producao = go.Figure()
    if not producao_data.empty:
        fig_producao.add_trace(go.Bar(
            x=producao_data['Turma/Semana'],
            y=producao_data['Valor'],
            marker_color=colors['primary'],
            width=0.5,
            name='Produção',
            text=producao_data['Valor'],
            textposition='auto',
        ))
        
        # Linha de meta (exemplo - 10% acima da média)
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
    
    # 6. Gráfico de Horas Extras (Pessoas)
    horas_extras_data = data[data['Tipo'] == 'Horas Extras'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])
    
    fig_horas_extras = go.Figure()
    if not horas_extras_data.empty:
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
    
    # 7. Gráfico de Treinamentos (Pessoas)
    fig_treinamentos = go.Figure()
    
    if not data.empty and 'Tipo' in data.columns:
        obrigatorios = data[data['Tipo'] == 'Treinamento Obrigatório'] if not data.empty else pd.DataFrame()
        eletivos = data[data['Tipo'] == 'Treinamento Eletivo'] if not data.empty else pd.DataFrame()
        
        if not obrigatorios.empty:
            fig_treinamentos.add_trace(go.Bar(
                x=obrigatorios['Turma/Semana'],
                y=obrigatorios['Valor'],
                name='Obrigatórios',
                marker_color=colors['negative'],
                text=obrigatorios['Valor'],
                textposition='auto',
            ))
        
        if not eletivos.empty:
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
    
    # 8. Gráfico de Faltas (Pessoas) - Dados de exemplo
   # 8. Gráfico de Faltas (Pessoas)
    faltas_data = data[data['Tipo'] == 'Faltas'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])

    fig_faltas = go.Figure()
    if not faltas_data.empty:
        fig_faltas.add_trace(go.Bar(
            x=faltas_data['Turma/Semana'],
            y=faltas_data['Valor'],
            marker_color=colors['warning'],
            text=faltas_data['Valor'],
            textposition='auto',
        ))

    fig_faltas.update_layout(
        title_text='Faltas por Semana',
        xaxis_title='Semana',
        yaxis_title='Quantidade',
        **layout_settings
    )
    
    # 9. Gráfico de Interrupção
    interrupcao_data = data[data['Tipo'] == 'Interrupção'] if not data.empty else pd.DataFrame(columns=['Turma/Semana', 'Valor'])
    
    fig_interrupcao = go.Figure()
    if not interrupcao_data.empty:
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
    
    # Linha de resumo de KPIs
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

# Rota para servir o formulário HTML
@app.server.route('/form')
def serve_form():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'form.html')

# Rota API para receber dados do formulário externo
@app.server.route('/api/add_data', methods=['POST'])
def add_data():
    try:
        new_data = request.json
        
        # Verifica se os dados básicos estão presentes
        if not all(key in new_data for key in ['Turma', 'Semana']):
            return jsonify({'error': 'Dados incompletos - Turma e Semana são obrigatórios'}), 400
            
        # Carrega os dados atuais
        current_data = load_data()
        
        # Cria registros individuais para cada indicador
        turma_semana = f"{new_data['Turma']} - {new_data['Semana']}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Mapeamento dos campos do formulário para os tipos de dados
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
        
        # Adiciona cada indicador como um registro separado
        for tipo, valor in indicators.items():
            if valor != 0:  # Só adiciona se o valor for diferente de zero
                record = {
                    'Turma/Semana': turma_semana,
                    'Tipo': tipo,
                    'Valor': float(valor),
                    'Timestamp': timestamp
                }
                current_data.append(record)
        
        # Salva os dados atualizados
        save_data(current_data)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# Rota API para limpar todos os dados
@app.server.route('/api/clear_data', methods=['POST'])
def clear_data():
    try:
        # Salva uma lista vazia no arquivo de dados
        save_data([])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# Callbacks para atualização dos gráficos
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
    """Atualiza todos os gráficos periodicamente."""
    # Carrega os dados mais recentes do arquivo
    data = load_data()
    df = pd.DataFrame(data)
    
    # Gera os gráficos atualizados
    (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
     fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao) = generate_graphs(df)
    
    # Atualiza o título com o horário da última atualização
    title = f"GESTÃO LAMINAÇÃO A FRIO (Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')})"
    
    return (fig_relatos, fig_acidentes, fig_sucata, fig_retrabalho, fig_producao,
            fig_horas_extras, fig_treinamentos, fig_faltas, fig_interrupcao, title)

# Executa o aplicativo
if __name__ == '__main__':
    app.run(debug=True)