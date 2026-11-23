import json
import sqlite3
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from schemas import ReclamacaoAnalise, ReclamacaoCSV, MetricasResponse
import pandas as pd


class ReclamacaoRepository:
    def __init__(self, db_path: str = "reclamacoes.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._inicializar_banco()
    
    def _inicializar_banco(self):
        """Cria a tabela se não existir."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reclamacoes (
                    id TEXT PRIMARY KEY,
                    texto_original TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    produto TEXT NOT NULL,
                    sentimento TEXT NOT NULL,
                    urgencia TEXT NOT NULL,
                    resumo TEXT NOT NULL,
                    data_registro TEXT,
                    canal TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
    
    def salvar(self, reclamacao: ReclamacaoAnalise) -> bool:
        """Salva uma reclamação analisada."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO reclamacoes 
                    (id, texto_original, categoria, produto, sentimento, urgencia, resumo, data_registro, canal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reclamacao.id,
                    reclamacao.texto_original,
                    reclamacao.categoria.value,
                    reclamacao.produto.value,
                    reclamacao.sentimento.value,
                    reclamacao.urgencia.value,
                    reclamacao.resumo,
                    reclamacao.data_registro,
                    reclamacao.canal
                ))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Erro ao salvar reclamação: {e}")
                return False
    
    def salvar_lote(self, reclamacoes: List[ReclamacaoAnalise]) -> int:
        """Salva múltiplas reclamações de uma vez."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                dados = [
                    (
                        r.id,
                        r.texto_original,
                        r.categoria.value,
                        r.produto.value,
                        r.sentimento.value,
                        r.urgencia.value,
                        r.resumo,
                        r.data_registro,
                        r.canal
                    )
                    for r in reclamacoes
                ]
                cursor.executemany("""
                    INSERT OR REPLACE INTO reclamacoes 
                    (id, texto_original, categoria, produto, sentimento, urgencia, resumo, data_registro, canal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, dados)
                conn.commit()
                count = cursor.rowcount
                conn.close()
                return count
            except Exception as e:
                print(f"Erro ao salvar lote: {e}")
                return 0
    
    def buscar_todas(self) -> List[ReclamacaoAnalise]:
        """Retorna todas as reclamações salvas."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reclamacoes ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            
            return [
                ReclamacaoAnalise(
                    id=row["id"],
                    texto_original=row["texto_original"],
                    categoria=row["categoria"],
                    produto=row["produto"],
                    sentimento=row["sentimento"],
                    urgencia=row["urgencia"],
                    resumo=row["resumo"],
                    data_registro=row["data_registro"],
                    canal=row["canal"]
                )
                for row in rows
            ]
    
    def buscar_por_id(self, id: str) -> Optional[ReclamacaoAnalise]:
        """Busca uma reclamação pelo ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reclamacoes WHERE id = ?", (id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return ReclamacaoAnalise(
                    id=row["id"],
                    texto_original=row["texto_original"],
                    categoria=row["categoria"],
                    produto=row["produto"],
                    sentimento=row["sentimento"],
                    urgencia=row["urgencia"],
                    resumo=row["resumo"],
                    data_registro=row["data_registro"],
                    canal=row["canal"]
                )
            return None
    
    def obter_metricas(self) -> MetricasResponse:
        """Calcula métricas agregadas para o dashboard."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total
            cursor.execute("SELECT COUNT(*) FROM reclamacoes")
            total = cursor.fetchone()[0]
            
            # Por categoria
            cursor.execute("SELECT categoria, COUNT(*) FROM reclamacoes GROUP BY categoria")
            por_categoria = dict(cursor.fetchall())
            
            # Por produto
            cursor.execute("SELECT produto, COUNT(*) FROM reclamacoes GROUP BY produto")
            por_produto = dict(cursor.fetchall())
            
            # Por sentimento
            cursor.execute("SELECT sentimento, COUNT(*) FROM reclamacoes GROUP BY sentimento")
            por_sentimento = dict(cursor.fetchall())
            
            # Por urgência
            cursor.execute("SELECT urgencia, COUNT(*) FROM reclamacoes GROUP BY urgencia")
            por_urgencia = dict(cursor.fetchall())
            
            conn.close()
            
            return MetricasResponse(
                total=total,
                por_categoria=por_categoria,
                por_produto=por_produto,
                por_sentimento=por_sentimento,
                por_urgencia=por_urgencia
            )
    
    def exportar_json(self) -> str:
        """Exporta todas as reclamações em JSON."""
        reclamacoes = self.buscar_todas()
        dados = [r.model_dump() for r in reclamacoes]
        return json.dumps(dados, ensure_ascii=False, indent=2)
    
    def exportar_csv(self) -> str:
        """Exporta todas as reclamações em CSV."""
        reclamacoes = self.buscar_todas()
        df = pd.DataFrame([r.model_dump() for r in reclamacoes])
        return df.to_csv(index=False, encoding='utf-8')
    
    def exportar_html(self) -> str:
        """Exporta relatório HTML consolidado com gráficos Chart.js."""
        reclamacoes = self.buscar_todas()
        metricas = self.obter_metricas()
        
        # Preparar dados para os gráficos
        categorias_labels = list(metricas.por_categoria.keys())
        categorias_data = list(metricas.por_categoria.values())
        
        produtos_labels = list(metricas.por_produto.keys())
        produtos_data = list(metricas.por_produto.values())
        
        sentimentos_labels = list(metricas.por_sentimento.keys())
        sentimentos_data = list(metricas.por_sentimento.values())
        
        urgencias_labels = list(metricas.por_urgencia.keys())
        urgencias_data = list(metricas.por_urgencia.values())
        
        # Tabela de reclamações
        linhas_tabela = ""
        for r in reclamacoes:
            urgencia_class = "urgencia-critica" if r.urgencia == "Crítica" else \
                           "urgencia-alta" if r.urgencia == "Alta" else \
                           "urgencia-media" if r.urgencia == "Média" else "urgencia-baixa"
            
            fraud_class = "fraude" if r.categoria == "Fraude/Segurança" else ""
            
            linhas_tabela += f"""
            <tr class="{fraud_class}">
                <td>{r.id}</td>
                <td>{r.data_registro or 'N/A'}</td>
                <td>{r.canal or 'N/A'}</td>
                <td>{r.categoria}</td>
                <td>{r.produto}</td>
                <td>{r.sentimento}</td>
                <td class="{urgencia_class}">{r.urgencia}</td>
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
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-critica {{ background: #fee2e2; color: #dc2626; }}
        .badge-alta {{ background: #ffedd5; color: #ea580c; }}
        .badge-media {{ background: #fef3c7; color: #d97706; }}
        .badge-baixa {{ background: #dcfce7; color: #16a34a; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FinGuard - Relatório de Triagem de Reclamações</h1>
            <p>Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Total de reclamações: {metricas.total}</p>
        </div>
        
        <div class="kpis">
            <div class="kpi">
                <h3>Total de Reclamações</h3>
                <div class="value">{metricas.total}</div>
            </div>
            <div class="kpi">
                <h3>Categorias Únicas</h3>
                <div class="value">{len(metricas.por_categoria)}</div>
            </div>
            <div class="kpi">
                <h3>Produtos Únicos</h3>
                <div class="value">{len(metricas.por_produto)}</div>
            </div>
            <div class="kpi">
                <h3>Urgência Crítica</h3>
                <div class="value" style="color: #dc2626;">{metricas.por_urgencia.get('Crítica', 0)}</div>
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
    
    def limpar_tudo(self) -> bool:
        """Remove todas as reclamações (útil para testes)."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM reclamacoes")
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Erro ao limpar banco: {e}")
                return False


# Instância global
repository = ReclamacaoRepository()