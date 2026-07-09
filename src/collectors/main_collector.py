"""
Módulo principal de coordenação dos coletores de dados
Executa coleta de todas as APIs governamentais de forma coordenada
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .ibge_collector import IBGECollector
from .bcb_collector import BCBCollector
from .transparencia_collector import TransparenciaCollector
from .dados_gov_collector import DadosGovCollector

class MainCollector:
    """Coordenador principal de todos os coletores de dados"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configurações padrão
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.parallel_execution = self.config.get('parallel_execution', True)
        self.max_workers = self.config.get('max_workers', 4)
        
        # Chaves de API (se disponíveis)
        self.transparencia_api_key = self.config.get('transparencia_api_key')
        
        # Inicializa coletores
        self.collectors = {
            'ibge': IBGECollector(timeout=self.timeout, max_retries=self.max_retries),
            'bcb': BCBCollector(timeout=self.timeout, max_retries=self.max_retries),
            'transparencia': TransparenciaCollector(
                timeout=self.timeout, 
                max_retries=self.max_retries,
                api_key=self.transparencia_api_key
            ),
            'dados_gov': DadosGovCollector(timeout=self.timeout, max_retries=self.max_retries)
        }
        
        # Diretório para salvar dados
        self.data_dir = self.config.get('data_dir', '/tmp/dashboard_data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def test_all_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com todas as APIs"""
        self.logger.info("Testando conectividade com todas as APIs")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total_apis': len(self.collectors),
                'successful': 0,
                'failed': 0,
                'requires_auth': 0
            }
        }
        
        for name, collector in self.collectors.items():
            try:
                self.logger.info(f"Testando conectividade: {name}")
                test_result = collector.test_connectivity()
                results['tests'][name] = test_result
                
                # Atualiza estatísticas
                if any(test_result.get(key, False) for key in test_result.keys() if key.startswith('api_')):
                    results['summary']['successful'] += 1
                else:
                    results['summary']['failed'] += 1
                
                # Verifica se requer autenticação
                if test_result.get('requires_auth', False) or test_result.get('auth_required', False):
                    results['summary']['requires_auth'] += 1
                    
            except Exception as e:
                self.logger.error(f"Erro ao testar {name}: {str(e)}")
                results['tests'][name] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results['summary']['failed'] += 1
        
        return results
    
    def _collect_single_source(self, name: str, collector: Any) -> Dict[str, Any]:
        """Coleta dados de uma única fonte"""
        try:
            self.logger.info(f"Iniciando coleta: {name}")
            start_time = time.time()
            
            result = collector.collect_all_data()
            
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'source': name,
                'success': result.get('success', False),
                'duration_seconds': round(duration, 2),
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta {name}: {str(e)}")
            return {
                'source': name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def collect_all_data_parallel(self) -> Dict[str, Any]:
        """Coleta dados de todas as fontes em paralelo"""
        self.logger.info("Iniciando coleta paralela de todas as fontes")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'execution_mode': 'parallel',
            'sources': {},
            'summary': {
                'total_sources': len(self.collectors),
                'successful': 0,
                'failed': 0,
                'total_duration_seconds': 0
            }
        }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submete todas as tarefas
            future_to_source = {
                executor.submit(self._collect_single_source, name, collector): name
                for name, collector in self.collectors.items()
            }
            
            # Coleta resultados conforme completam
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    result = future.result()
                    results['sources'][source_name] = result
                    
                    if result.get('success', False):
                        results['summary']['successful'] += 1
                    else:
                        results['summary']['failed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar resultado de {source_name}: {str(e)}")
                    results['sources'][source_name] = {
                        'source': source_name,
                        'success': False,
                        'error': f"Erro ao processar resultado: {str(e)}",
                        'timestamp': datetime.now().isoformat()
                    }
                    results['summary']['failed'] += 1
        
        end_time = time.time()
        results['summary']['total_duration_seconds'] = round(end_time - start_time, 2)
        
        return results
    
    def collect_all_data_sequential(self) -> Dict[str, Any]:
        """Coleta dados de todas as fontes sequencialmente"""
        self.logger.info("Iniciando coleta sequencial de todas as fontes")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'execution_mode': 'sequential',
            'sources': {},
            'summary': {
                'total_sources': len(self.collectors),
                'successful': 0,
                'failed': 0,
                'total_duration_seconds': 0
            }
        }
        
        start_time = time.time()
        
        for name, collector in self.collectors.items():
            result = self._collect_single_source(name, collector)
            results['sources'][name] = result
            
            if result.get('success', False):
                results['summary']['successful'] += 1
            else:
                results['summary']['failed'] += 1
            
            # Pausa entre coletas para evitar sobrecarga
            time.sleep(1)
        
        end_time = time.time()
        results['summary']['total_duration_seconds'] = round(end_time - start_time, 2)
        
        return results
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Coleta dados de todas as fontes (paralelo ou sequencial)"""
        if self.parallel_execution:
            return self.collect_all_data_parallel()
        else:
            return self.collect_all_data_sequential()
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Salva resultados em arquivo JSON
        
        Args:
            results: Dados para salvar
            filename: Nome do arquivo (opcional)
        
        Returns:
            Caminho do arquivo salvo
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coleta_completa_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Resultados salvos em: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultados: {str(e)}")
            raise
    
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """Gera relatório resumido dos resultados"""
        summary = results.get('summary', {})
        timestamp = results.get('timestamp', 'N/A')
        
        report = f"""
=== RELATÓRIO DE COLETA DE DADOS ===
Timestamp: {timestamp}
Modo de execução: {results.get('execution_mode', 'N/A')}
Duração total: {summary.get('total_duration_seconds', 0)} segundos

=== RESUMO ===
Total de fontes: {summary.get('total_sources', 0)}
Sucessos: {summary.get('successful', 0)}
Falhas: {summary.get('failed', 0)}
Taxa de sucesso: {(summary.get('successful', 0) / max(summary.get('total_sources', 1), 1) * 100):.1f}%

=== DETALHES POR FONTE ===
"""
        
        for source_name, source_data in results.get('sources', {}).items():
            success = source_data.get('success', False)
            duration = source_data.get('duration_seconds', 0)
            status = "✓ SUCESSO" if success else "✗ FALHA"
            
            report += f"{source_name.upper()}: {status} ({duration}s)\n"
            
            if not success and 'error' in source_data:
                report += f"  Erro: {source_data['error']}\n"
            
            # Adiciona detalhes específicos se disponível
            data = source_data.get('data', {})
            if isinstance(data, dict) and 'errors' in data and data['errors']:
                report += f"  Erros específicos: {', '.join(data['errors'])}\n"
        
        return report


if __name__ == "__main__":
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Teste do coletor principal
    collector = MainCollector()
    
    print("=== Teste de Conectividade ===")
    connectivity = collector.test_all_connectivity()
    print(f"APIs funcionais: {connectivity['summary']['successful']}/{connectivity['summary']['total_apis']}")
    
    print("\n=== Coleta Completa ===")
    results = collector.collect_all_data()
    
    # Salva resultados
    filepath = collector.save_results(results)
    print(f"Resultados salvos em: {filepath}")
    
    # Gera relatório
    report = collector.generate_summary_report(results)
    print(report)

