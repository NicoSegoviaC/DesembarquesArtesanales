import pandas as pd
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

df = pd.read_csv('DESEMBARQUESPESQUEROS_SERNAPESCA_2000-2022_DATACENTER_MODIFICADO.csv', encoding='utf-8', sep=";", low_memory=False)

##defino variable meses para hacer la sumatoria.
meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']

# Crear la columna 'desembarque (Tons)'
df['desembarque (Tons)'] = df[meses].sum(axis=1)
df['AÑO'] = df['AÑO'].astype(int)

def int_to_roman(input):
    """ Convert an integer to a Roman numeral. """
    if input == "AI":
        return "AGUAS INTERNACIONALES"
    if not isinstance(input, type(1)):
        raise TypeError("expected integer, got %s" % type(input))
    if not 0 < input < 4000:
        raise ValueError("Argument must be between 1 and 3999")
    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return ''.join(result)

# Convertir la columna de regiones a números romanos y agregar la palabra "REGIÓN" al final
df['REGION_NAME'] = df['REGION'].apply(lambda x: int_to_roman(int(x)) + " REGIÓN" if str(x).isdigit() and x != 99 else int_to_roman(x))


# Inicializar la app
app = dash.Dash(__name__)
server = app.server

# Obtener la lista de especies y regiones únicas
especies = sorted(df["ESPECIE"].unique())
regiones = sorted([r for r in df["REGION_NAME"].unique() if isinstance(r, str)])

# Definir la estructura de la app
app.layout = html.Div([
  
    # Encabezado con el título y los logos
    html.Div([
        html.H1('Desembarques pesqueros artesanales (2000-2022)', style={'display': 'inline-block', 'margin-right': 'px'}),
        html.Img(src='/assets/DC_Logo.png', style={'height':'15%', 'width':'15%', 'display': 'inline-block', 'margin-right': '20px'}), # Logo 1
        html.Img(src='/assets/infografia-pesqueria-artesanal.png', style={'height':'10%', 'width':'10%', 'display': 'inline-block'}), # Logo 2
    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}),

    dcc.Dropdown(
        id='nivel-dropdown',
        options=[{'label': 'Nivel nacional', 'value': 'Nivel nacional'},
                 {'label': 'Region', 'value': 'Region'}],
        value='Nivel nacional'
    ),
    dcc.Dropdown(
        id='especie-dropdown',
        options=[{'label': especie, 'value': especie} for especie in especies],
        value=especies[0]
    ),
    dcc.Dropdown(
        id='region-dropdown',
        options=[{'label': region, 'value': region} for region in regiones],
        value=regiones[0],
        style={'display': 'none'}
    ),
    html.Div([
        html.Label("Ingresar rango de años:"),
        dcc.Input(id='year-start', type='number', placeholder='Año inicio'),
        dcc.Input(id='year-end', type='number', placeholder='Año final'),
    ]),
    dcc.Graph(id='especie-graph')
])


@app.callback(
    Output('especie-graph', 'figure'),
    [Input('especie-dropdown', 'value'),
     Input('nivel-dropdown', 'value'),
     Input('region-dropdown', 'value'),
     Input('year-start', 'value'),
     Input('year-end', 'value')]
)
def update_figure(selected_especie, nivel, region, year_start, year_end):
    
    # Filtrar por rango de años si se proveen valores
    if year_start and year_end:
        df_filtered = df[(df["AÑO"] >= year_start) & (df["AÑO"] <= year_end)]
    else:
        df_filtered = df
    
    if nivel == 'Nivel nacional':
        df_especie = df_filtered[df_filtered["ESPECIE"] == selected_especie]
    else:  # Nivel de región
        df_especie = df_filtered[(df_filtered["ESPECIE"] == selected_especie) & (df_filtered["REGION_NAME"] == region)]

    # Comprobar si df_especie tiene registros
    if df_especie.empty:
        return go.Figure(
            layout=go.Layout(
                title=f"Sin registros de desembarque para {selected_especie} en el rango solicitado"
            )
        )

    df_especie_aggregated = df_especie.groupby("AÑO")["desembarque (Tons)"].sum().reset_index()

    # Calcular desembarque total promedio y desviación estándar
    avg_desembarque = df_especie["desembarque (Tons)"].mean()
    std_desembarque = df_especie["desembarque (Tons)"].std()

    # Identificar la comuna con más desembarques en promedio y su provincia
    df_comuna_avg = df_especie.groupby("COMUNA")[["desembarque (Tons)"]].mean().reset_index()
    top_comuna = df_comuna_avg.sort_values(by="desembarque (Tons)", ascending=False).iloc[0]
    provincia_top_comuna = df_especie[df_especie["COMUNA"] == top_comuna["COMUNA"]]["PROVINCIA"].iloc[0]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_especie_aggregated["AÑO"],
        y=df_especie_aggregated["desembarque (Tons)"],
        mode='lines+markers',
        name="Desembarque total",
        line=dict(color='grey', width=1)
    ))

    fig.update_layout(title=f"Desembarque total anual de {selected_especie}",
                      xaxis_title="Año",
                      yaxis_title="Desembarque (Tons.)",
                      xaxis=dict(tickvals=df_especie_aggregated["AÑO"].unique()),  # Esta línea asegura que todos los años se muestren en el eje x
                      legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      showlegend=False,
                      template="plotly_white",
                      annotations=[
                          dict(
                              text=f"<b>Desembarque total promedio (toneladas)</b> = {avg_desembarque:.2f} ± {std_desembarque:.2f}",
                              xref="paper", yref="paper",
                              x=1, y=1.1,
                              showarrow=False,
                              xanchor="right", yanchor="top",
                              font=dict(size=12)
                          ),
                          dict(
                              text=f"<b>Comuna con más desembarques en promedio</b>: {top_comuna['COMUNA']} ({provincia_top_comuna})",
                              xref="paper", yref="paper",
                              x=1, y=1.05,
                              showarrow=False,
                              xanchor="right", yanchor="top",
                              font=dict(size=12)
                          ),
                          dict(
                              text="Fuente: Sernapesca. Elaboración: DataCenter",
                              xref="paper", yref="paper",
                              x=1, y=0.01,
                              showarrow=False,
                              xanchor="right", yanchor="bottom",
                              font=dict(size=10)
                          )
                      ]
                      )

    return fig


@app.callback(
    Output('region-dropdown', 'style'),
    [Input('nivel-dropdown', 'value')]
)
def toggle_region_dropdown(nivel):
    if nivel == 'Region':
        return {'display': 'block'}
    else:
        return {'display': 'none'}

# Iniciar la app
if __name__ == '__main__':
    app.run_server(debug=True, port=8000)
