from typing import List
from schemas import ReclamacaoAnalise
import json
import pandas as pd
from datetime import datetime


class Exporter:
    """Gerador de relatórios de exportação."""
    
    @staticmethod
    def to_json(reclamacoes: List[ReclamacaoAnalise]) -> str:
        """Exporta para JSON."""
        dados = [r.model_dump() for r in reclamacoes]
        return json.dumps(dados, ensure_ascii=False, indent=2)
    
    @staticmethod
    def to_csv(reclamacoes: List[ReclamacaoAnalise]) -> str:
        """Exporta para CSV."""
        df = pd.DataFrame([r.model_dump() for r in reclamacoes])
        return df.to_csv(index=False, encoding='utf-8')
    
    @staticmethod
    def to_html(reclamacoes: List[ReclamacaoAnalise]) -> str:
        """Exporta para HTML consolidado com gráficos Chart.js."""
        if not reclamacoes:
            return "<html><body><h1>Nenhuma reclamação para exportar</h1></body></html>"
        
        # Calcular métricas
        por_categoria = {}
        por_produto = {}
        por_sentimento = {}
        por_urgencia = {}
        
        for r in reclamacoes:
            por_categoria[r.categoria.value] = por_categoria.get(r.categoria.value, 0) + 1
            por_produto[r.produto.value] = por_produto.get(r.produto.value, 0) + 1
            por_sentimento[r.sentimento.value] = por_sentimento.get(r.sentimento.value, 0) + 1
            por_urgencia[r.urgencia.value] = por_urgencia.get(r.urgencia.value, 0) + 1
        
        categorias_labels = list(por_categoria.keys())
        categorias_data = list(por_categoria.values())
        
        produtos_labels = list(por_produto.keys())
        produtos_data = list(por_produto.values())
        
        sentimentos_labels = list(por_sentimento.keys())
        sentimentos_data = list(por_sentimento.values())
        
        urgencias_labels = list(por_urgencia.keys())
        urgencias_data = list(por_urgencia.values())
        
        # Tabela de reclamações
        linhas_tabela = ""
        for r in reclamacoes:
            urgencia_class = "urgencia-critica" if r.urgencia.value == "Crítica" else \
                           "urgencia-alta" if r.urgencia.value == "Alta" else \
                           "urgencia-media" if r.urgencia.value == "Média" else "urgencia-baixa"
            
            fraud_class = "fraude" if r.categoria.value == "Fraude/Segurança" else ""
            
            linhas_tabela += f"""
            <tr class="{fraud_class}">
                <td>{r.id}</td>
                <td>{r.data_registro or 'N/A'}</td>
                <td>{r.canal or 'N/A'}</td>
                <td>{r.categoria.value}</td>
                <td>{r.produto.value}</td>
                <td>{r.sentimento.value}</td>
                <td class="{urgencia_class}">{r.urgencia.value}</td>
                <td>{r.resumo[:100]}...</td>
            </tr>"""
        
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinGuard - Relatório de Reclamações</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .header h1 {{ margin: 0; color: #1f2937; }}
        .header p {{ margin: 10px 0 0; color: #6b7280; }}
        .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
        .kpi {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .kpi h3 {{ margin: 0 0 8px; font-size: 14px; color: #6b7280; font-weight: 500; }}
        .kpi .value {{ font-size: 32px; font-weight: 700; color: #1f2937; }}
        .charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .chart-card h3 {{ margin: 0 0 16px; font-size: 16px; color: #1f2937; }}
        .table-card {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; color: #374151; }}
        tr:hover {{ background: #f9fafb; }}
        .urgencia-critica {{ background: #fef2f2; }}
        .urgencia-alta {{ background: #fff7ed; }}
        .urgencia-media {{ background: #fffbeb; }}
        .urgencia-baixa {{ background: #f0fdf4; }}
        .fraude td:nth-child(4) {{ font-weight: 700; color: #dc2626; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FinGuard - Relatório de Triagem de Reclamações</h1>
            <p>Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Total de reclamações: {len(reclamacoes)}</p>
        </div>
        
        <div class="kpis">
            <div class="kpi">
                <h3>Total de Reclamações</h3>
                <div class="value">{len(reclamacoes)}</div>
            </div>
            <div class="kpi">
                <h3>Categorias Únicas</h3>
                <div class="value">{len(por_categoria)}</div>
            </div>
            <div class="kpi">
                <h3>Produtos Únicos</h3>
                <div class="value">{len(por_produto)}</div>
            </div>
            <div class="kpi">
                <h3>Urgência Crítica</h3>
                <div class="value" style="color: #dc2626;">{por_urgencia.get('Crítica', 0)}</div>
            </div>
        </div>
        
        <div class="charts">
            <div class="chart-card">
                <h3>Por Categoria</h3>
                <canvas id="categoriaChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Por Produto</h3>
                <canvas id="produtoChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Por Sentimento</h3>
                <canvas id="sentimentoChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Por Urgência</h3>
                <canvas id="urgenciaChart"></canvas>
            </div>
        </div>
        
        <div class="table-card">
            <h3 style="padding: 20px; margin: 0;">Detalhamento das Reclamações</h3>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Data</th>
                            <th>Canal</th>
                            <th>Categoria</th>
                            <th>Produto</th>
                            <th>Sentimento</th>
                            <th>Urgência</th>
                            <th>Resumo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {linhas_tabela}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // Gráfico de Categorias
        new Chart(document.getElementById('categoriaChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(categorias_labels, ensure_ascii=False)},
                datasets: [{{
                    data: {json.dumps(categorias_data)},
                    backgroundColor: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#6b7280']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: true }}
        }});
        
        // Gráfico de Produtos
        new Chart(document.getElementById('produtoChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(produtos_labels, ensure_ascii=False)},
                datasets: [{{
                    label: 'Quantidade',
                    data: {json.dumps(produtos_data)},
                    backgroundColor: '#3b82f6'
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: true, indexAxis: 'y' }}
        }});
        
        // Gráfico de Sentimentos
        new Chart(document.getElementById('sentimentoChart'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps(sentimentos_labels, ensure_ascii=False)},
                datasets: [{{
                    data: {json.dumps(sentimentos_data)},
                    backgroundColor: ['#10b981', '#6b7280', '#ef4444', '#dc2626']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: true }}
        }});
        
        // Gráfico de Urgências
        new Chart(document.getElementById('urgenciaChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(urgencias_labels, ensure_ascii=False)},
                datasets: [{{
                    label: 'Quantidade',
                    data: {json.dumps(urgencias_data)},
                    backgroundColor: ['#16a34a', '#d97706', '#ea580c', '#dc2626']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: true }}
        }});
    </script>
</body>
</html>"""
        return html


# Instância global
exporter = Exporter()