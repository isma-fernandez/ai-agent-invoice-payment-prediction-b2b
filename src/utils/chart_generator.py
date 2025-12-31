import plotly.graph_objects as go
import plotly.express as px
import uuid
from typing import Dict
from src.data.models import ChartType

class ChartGenerator:
    """Genera gráficos para el agente financiero."""

    def __init__(self):
        self.charts: Dict[str, go.Figure] = {}
        self.colors = {
            'primary': '#1f77b4',
            'danger': '#d62728',
            'warning': '#ff7f0e',
            'success': '#2ca02c',
            'neutral': '#7f7f7f',
            'palette': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        }

    async def create_chart(self, chart_type: ChartType, title: str,
                           data: dict, show_values: bool = True) -> str:
        """Crea un gráfico y devuelve su ID."""
        chart_id = str(uuid.uuid4())[:8]

        if chart_type == ChartType.BAR:
            fig = self._create_bar_chart(data, title, show_values, horizontal=False)
        elif chart_type == ChartType.HORIZONTAL_BAR:
            fig = self._create_bar_chart(data, title, show_values, horizontal=True)
        elif chart_type == ChartType.LINE:
            fig = self._create_line_chart(data, title, show_values)
        elif chart_type == ChartType.PIE:
            fig = self._create_pie_chart(data, title, show_values, donut=False)
        elif chart_type == ChartType.DONUT:
            fig = self._create_pie_chart(data, title, show_values, donut=True)
        else:
            raise ValueError(f"Tipo de gráfico no soportado: {chart_type}")

        # TEMA OSCURO
        fig.update_layout(
            template='plotly_dark',  # ← Tema oscuro
            title=dict(text=title, font=dict(size=16, color='#FAFAFA')),
            font=dict(family="Arial", size=12, color='#FAFAFA'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40),
            height=400,
            legend=dict(
                bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA')
            )
        )

        self.charts[chart_id] = fig
        return chart_id


    def _create_bar_chart(self, data: dict, title: str,
                          show_values: bool, horizontal: bool) -> go.Figure:
        labels = data.get('labels', [])

        if 'series' in data:
            fig = go.Figure()
            for i, series in enumerate(data['series']):
                if horizontal:
                    fig.add_trace(go.Bar(
                        y=labels, x=series['values'],
                        name=series['name'],
                        orientation='h',
                        marker_color=self.colors['palette'][i % len(self.colors['palette'])],
                        text=series['values'] if show_values else None,
                        textposition='outside'
                    ))
                else:
                    fig.add_trace(go.Bar(
                        x=labels, y=series['values'],
                        name=series['name'],
                        marker_color=self.colors['palette'][i % len(self.colors['palette'])],
                        text=series['values'] if show_values else None,
                        textposition='outside'
                    ))
            fig.update_layout(barmode='group')
        else:
            values = data.get('values', [])
            if horizontal:
                fig = go.Figure(go.Bar(
                    y=labels, x=values,
                    orientation='h',
                    marker_color=self.colors['primary'],
                    text=values if show_values else None,
                    textposition='outside'
                ))
            else:
                fig = go.Figure(go.Bar(
                    x=labels, y=values,
                    marker_color=self.colors['primary'],
                    text=values if show_values else None,
                    textposition='outside'
                ))

        return fig


    def _create_line_chart(self, data: dict, title: str, show_values: bool) -> go.Figure:
        labels = data.get('labels', [])
        fig = go.Figure()

        if 'series' in data:
            for i, series in enumerate(data['series']):
                fig.add_trace(go.Scatter(
                    x=labels, y=series['values'],
                    mode='lines+markers' + ('+text' if show_values else ''),
                    name=series['name'],
                    line=dict(color=self.colors['palette'][i % len(self.colors['palette'])]),
                    text=series['values'] if show_values else None,
                    textposition='top center'
                ))
        else:
            values = data.get('values', [])
            fig.add_trace(go.Scatter(
                x=labels, y=values,
                mode='lines+markers' + ('+text' if show_values else ''),
                line=dict(color=self.colors['primary']),
                text=values if show_values else None,
                textposition='top center'
            ))

        return fig


    def _create_pie_chart(self, data: dict, title: str,
                          show_values: bool, donut: bool) -> go.Figure:
        labels = data.get('labels', [])
        values = data.get('values', [])

        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.4 if donut else 0,
            marker=dict(colors=self.colors['palette']),
            textinfo='label+percent' if show_values else 'label',
            textposition='outside'
        ))

        return fig


    def get_chart(self, chart_id: str) -> go.Figure | None:
        """Recupera un gráfico por su ID."""
        return self.charts.get(chart_id)


    def clear_chart(self, chart_id: str):
        """Elimina un gráfico de la memoria."""
        if chart_id in self.charts:
            del self.charts[chart_id]


chart_generator = ChartGenerator()