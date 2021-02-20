# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_auth
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
from data_parser import DataParser

# Keep this out of source code repository - save in a file or a database
# Here just to demonstrate this authentication possibility
VALID_USERNAME_PASSWORD_PAIRS = {
    'user': 'user'
}

external_stylesheets = [
        #'https://codepen.io/chriddyp/pen/bWLwgP.css'
        dbc.themes.FLATLY
    ]


# Create the app, figures and define layout
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)


def create_dataframes():
    # Parse letters to a Pandas DataFrame
    data_parser = DataParser()
    df = data_parser.letters_to_df()

    # Word count DataFrame
    word_counts = df.groupby(['ID', 'Year']).size().to_frame(name = 'WordCount').reset_index()

    # POS counts for each letter
    pos_counts = df.groupby(['ID', 'Tags', 'Year', 'WordCount']).size().to_frame(name = 'PosCount').reset_index()
    pos_counts['PosCountNorm'] = pos_counts['PosCount']/pos_counts['WordCount']*100

    # NN1 tag count per year
    nn1_counts = pos_counts[pos_counts['Tags'] == 'NN1']
    nn1_counts = nn1_counts.groupby(['Year']).mean().reset_index()

    pos_set = set(df['Tags'])
    pos_list = [{'label':tag, 'value':tag} for tag in pos_set]

    return word_counts, pos_counts, nn1_counts, pos_list


word_counts, pos_counts, nn1_counts, pos_list = create_dataframes()

wc_fig = px.scatter(word_counts, x="Year", y="WordCount", title='Word count for each letter in corpus')
#pc_fig = px.line(nn1_counts, x="Year", y="PosCountNorm")

app.layout = html.Div(children=[
    # We could possible divide the app into multiple tabs, then user could 
    # change the visible layout by clicking nav bar items. However, data should
    # most likely be stored outside the layout as otherwise changin tab will
    # result in data loss.
    html.Nav(
        className ='navbar navbar-expand-lg navbar-dark bg-primary', 
        children=[
            html.H1(className='navbar-brand', children='Data Science Project: Language variation')
            # , html.A('Tab1', className="nav-item nav-link", href='/apps/Tab1')
            # , html.A('Tab2', className="nav-item nav-link", href='/apps/Tab2')
        ]) 

    # Simple word count graph    
    , html.Div(
        children=[
            dcc.Graph(
                id='word-count-graph',
                figure=wc_fig
            )])

    # POS amount per year
    , html.Div(
        children=[
            dcc.Graph(id='pos_graph')
            , dcc.Dropdown(
                id='pos_dropdown',
                options=pos_list,
                value=['NN1'],
                multi=True
            )])

    # POS group comparison
    , html.Div(
        children=[
            dcc.Graph(id='pos_groups_graph')
            , html.P(children='Group 1')
            , dcc.Dropdown(
                id='pos_groups_dropdown_1',
                options=pos_list,
                value=['NN', 'NN1'],
                multi=True
            )  
            , html.P(children='Group 2')
            , dcc.Dropdown(
                id='pos_groups_dropdown_2',
                options=pos_list,
                value=['VBR', 'VB'],
                multi=True
            )])])


@app.callback(Output('pos_graph', 'figure'), [Input('pos_dropdown', 'value')])

def display_pos_graphs(selected_values):
    if selected_values is None:
        raise PreventUpdate
    else:
        mask = pos_counts['Tags'].isin(selected_values)
        fig = px.line(
            data_frame=pos_counts[mask].groupby(['Tags', 'Year']).mean().reset_index(), 
            x="Year", 
            y="PosCountNorm", 
            range_y=[0,50],
            labels={
                'Year': 'Year', 
                'PosCountNorm':'%'},
            color='Tags',
            title='Percentage of POS per year')
        return fig


@app.callback(
    Output('pos_groups_graph', 'figure'), 
    [Input('pos_groups_dropdown_1', 'value'),
    Input('pos_groups_dropdown_2', 'value')])

def display_grouped_pos_graphs(values1, values2):
    if values1 is None and values2 is None:
        raise PreventUpdate
    else:
        fig = go.Figure()
        mask = pos_counts['Tags'].isin(values1)
        fig.add_scatter(
            x=pos_counts[mask].groupby(['Tags', 'Year']).mean().reset_index().groupby(['Year']).sum().reset_index()['Year'], 
            y=pos_counts[mask].groupby(['Tags', 'Year']).mean().reset_index().groupby(['Year']).sum().reset_index()['PosCountNorm'],
            name='Group 1')

        mask = pos_counts['Tags'].isin(values2)
        fig.add_scatter(
            x=pos_counts[mask].groupby(['Tags', 'Year']).mean().reset_index().groupby(['Year']).sum().reset_index()['Year'], 
            y=pos_counts[mask].groupby(['Tags', 'Year']).mean().reset_index().groupby(['Year']).sum().reset_index()['PosCountNorm'],
            name='Group 2')
        fig.update_layout(yaxis_range=[0,50], title='Build POS groups and compare')
        return fig


if __name__ == '__main__':
    app.run_server(debug=True)
