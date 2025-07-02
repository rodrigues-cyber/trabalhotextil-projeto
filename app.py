
from flask import Flask, render_template, request, redirect, url_for, session
from markupsafe import Markup
import mysql.connector
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)
app.secret_key = 'segredo123'

DB_CONFIG = {
    'host': "34.176.167.17",
    'user': "projeto",
    'password': "projeto",
    'database': "maquinas"
}

def obter_dados_maquina(tabela):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {tabela} ORDER BY RAND() LIMIT 1;")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return {
            'temperatura': row[1],
            'pressao': row[2],
            'tempo': row[3] * 60,
            'vazao': row[4],
            'ph': row[5],
            'valvula': row[6],
            'timestamp': row[7]
        }
    else:
        return {}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        if usuario == 'admin' and senha == '123456789':
            session['usuario'] = usuario
            return redirect(url_for('resumo'))
        else:
            erro = 'Usuário ou senha inválidos'
    return render_template('login.html', erro=erro)

@app.route('/resumo')
def resumo():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('resumo.html')

@app.route('/maquina<int:n>')
def maquina_n(n):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    nome_tabela = f"maquina0{n}" if n < 10 else f"maquina{n}"
    sensores = obter_dados_maquina(nome_tabela)
    return render_template(f'maquina{n}.html', sensores=sensores)

@app.route('/maquina<int:n>/graficos')
def graficos_maquina(n):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    nome_tabela = f"maquina0{n}" if n < 10 else f"maquina{n}"

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        query = f'''
            SELECT horario, temperatura, pressao, tempo_exposicaos, vazao, ph
            FROM {nome_tabela}
            ORDER BY horario DESC
            LIMIT 50
        '''
        df = pd.read_sql(query, conn)
        conn.close()
        df = df.sort_values("horario")

        def grafico_linha(y, titulo, yaxis, cor='blue'):

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['horario'], y=df[y], mode='lines+markers', line=dict(shape='spline', color=cor)))

            # Adiciona linha de regressão linear apenas para temperatura ou pressão
            if y in ['temperatura', 'pressao']:
                import numpy as np
                x_vals = np.arange(len(df))
                y_vals = df[y].values
                from scipy import stats
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
                trendline = slope * x_vals + intercept
                fig.add_trace(go.Scatter(
                    x=df['horario'],
                    y=trendline,
                    mode='lines',
                    name='Tendência Linear',
                    line=dict(dash='dash', color='black')
                ))

            fig.update_layout(title=titulo, xaxis_title='Data/Hora', yaxis_title=yaxis, template='plotly_white')
            return pio.to_html(fig, full_html=False)


        def grafico_barras(y, titulo, yaxis):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['horario'], y=df[y]))
            fig.update_layout(title=titulo, xaxis_title='Data/Hora', yaxis_title=yaxis, template='plotly_white')
            return pio.to_html(fig, full_html=False)

        def grafico_dispersao(x, y, titulo, xaxis, yaxis):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='markers'))
            fig.update_layout(title=titulo, xaxis_title=xaxis, yaxis_title=yaxis, template='plotly_white')
            return pio.to_html(fig, full_html=False)

        graficos_html = {
            'grafico_temp': grafico_linha('temperatura', 'Temperatura (°C)', '°C', cor='red'),
            'grafico_pressao': grafico_linha('pressao', 'Pressão (Pa)', 'Pa'),
            'grafico_vazao': grafico_barras('vazao', 'Vazão (L/min)', 'L/min'),
            'grafico_ph': grafico_dispersao('ph', 'ph', 'pH x Condutividade', 'pH', 'Condutividade'),
            'grafico_tempo': grafico_linha('tempo_exposicaos', 'Tempo de Trabalho - Curva PF', 'Segundos')
        }

        return render_template(f"grafico_maquina{n}.html", n=n, **graficos_html)

    except Exception as e:
        return f"Erro ao gerar gráficos: {e}"

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
