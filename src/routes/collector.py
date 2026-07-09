"""
Rotas Flask para o sistema de coleta de dados
"""

from flask import Blueprint, jsonify, request
import logging
import os
from datetime import datetime

from src.collectors.main_collector import MainCollector

collector_bp = Blueprint('collector', __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instância global do coletor
main_collector = None

def get_collector():
    """Obtém instância do coletor principal"""
    global main_collector
    if main_collector is None:
        config = {
            'timeout': 30,
            'max_retries': 3,
            'parallel_execution': True,
            'max_workers': 4,
            'data_dir': os.path.join(os.path.dirname(__file__), '..', 'data'),
            'transparencia_api_key': os.environ.get('TRANSPARENCIA_API_KEY')
        }
        main_collector = MainCollector(config)
    return main_collector

@collector_bp.route('/status', methods=['GET'])
def get_status():
    """Retorna status do sistema de coleta"""
    try:
        return jsonify({
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'collectors': ['ibge', 'bcb', 'transparencia', 'dados_gov']
        })
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/test-connectivity', methods=['GET'])
def test_connectivity():
    """Testa conectividade com todas as APIs"""
    try:
        collector = get_collector()
        results = collector.test_all_connectivity()
        return jsonify(results)
    except Exception as e:
        logger.error(f"Erro ao testar conectividade: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/collect', methods=['POST'])
def collect_data():
    """Executa coleta completa de dados"""
    try:
        # Parâmetros opcionais
        data = request.get_json() or {}
        parallel = data.get('parallel', True)
        save_results = data.get('save_results', True)
        
        collector = get_collector()
        collector.parallel_execution = parallel
        
        logger.info(f"Iniciando coleta de dados (paralelo: {parallel})")
        results = collector.collect_all_data()
        
        # Salva resultados se solicitado
        if save_results:
            try:
                filepath = collector.save_results(results)
                results['saved_file'] = filepath
            except Exception as e:
                logger.warning(f"Erro ao salvar resultados: {str(e)}")
                results['save_error'] = str(e)
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Erro durante coleta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/collect/<source>', methods=['POST'])
def collect_single_source(source):
    """Executa coleta de uma fonte específica"""
    try:
        collector = get_collector()
        
        if source not in collector.collectors:
            return jsonify({
                'error': f'Fonte não encontrada: {source}',
                'available_sources': list(collector.collectors.keys())
            }), 404
        
        logger.info(f"Iniciando coleta da fonte: {source}")
        
        # Executa coleta da fonte específica
        single_collector = collector.collectors[source]
        result = collector._collect_single_source(source, single_collector)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao coletar fonte {source}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/sources', methods=['GET'])
def get_sources():
    """Lista todas as fontes de dados disponíveis"""
    try:
        collector = get_collector()
        
        sources_info = {}
        for name, collector_instance in collector.collectors.items():
            sources_info[name] = {
                'name': name,
                'class': collector_instance.__class__.__name__,
                'description': collector_instance.__doc__ or 'Sem descrição disponível'
            }
        
        return jsonify({
            'sources': sources_info,
            'total': len(sources_info)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar fontes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/config', methods=['GET'])
def get_config():
    """Retorna configuração atual do sistema"""
    try:
        collector = get_collector()
        
        config_info = {
            'timeout': collector.timeout,
            'max_retries': collector.max_retries,
            'parallel_execution': collector.parallel_execution,
            'max_workers': collector.max_workers,
            'data_dir': collector.data_dir,
            'has_transparencia_key': bool(collector.transparencia_api_key)
        }
        
        return jsonify(config_info)
        
    except Exception as e:
        logger.error(f"Erro ao obter configuração: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/config', methods=['PUT'])
def update_config():
    """Atualiza configuração do sistema"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados de configuração não fornecidos'}), 400
        
        collector = get_collector()
        
        # Atualiza configurações permitidas
        if 'timeout' in data:
            collector.timeout = int(data['timeout'])
        if 'max_retries' in data:
            collector.max_retries = int(data['max_retries'])
        if 'parallel_execution' in data:
            collector.parallel_execution = bool(data['parallel_execution'])
        if 'max_workers' in data:
            collector.max_workers = int(data['max_workers'])
        
        return jsonify({
            'message': 'Configuração atualizada com sucesso',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.route('/report', methods=['POST'])
def generate_report():
    """Gera relatório baseado em resultados de coleta"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({'error': 'Resultados de coleta não fornecidos'}), 400
        
        collector = get_collector()
        report = collector.generate_summary_report(data['results'])
        
        return jsonify({
            'report': report,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        return jsonify({'error': str(e)}), 500

@collector_bp.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@collector_bp.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    return jsonify({'error': 'Erro interno do servidor'}), 500

