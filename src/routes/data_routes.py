"""
Rotas Flask para o sistema integrado de dados
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

from src.services.data_service import DataService

data_bp = Blueprint('data', __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instância global do serviço de dados
data_service = None

def get_data_service():
    """Obtém instância do serviço de dados"""
    global data_service
    if data_service is None:
        from flask import current_app
        config = {
            'enable_auto_collection': False,
            'auto_collection_interval': 3600,  # 1 hora
            'collector': {
                'parallel_execution': True,
                'max_workers': 4,
                'timeout': 30,
                'max_retries': 3
            }
        }
        data_service = DataService(current_app, config)
    return data_service

@data_bp.route('/status', methods=['GET'])
def get_service_status():
    """Retorna status do serviço de dados"""
    try:
        service = get_data_service()
        stats = service.get_service_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Erro ao obter status do serviço: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/collect', methods=['POST'])
def collect_data():
    """Executa coleta completa com processamento e armazenamento"""
    try:
        # Parâmetros opcionais
        data = request.get_json() or {}
        save_to_db = data.get('save_to_db', True)
        use_cache = data.get('use_cache', True)
        
        service = get_data_service()
        
        logger.info("Iniciando coleta completa de dados")
        result = service.collect_and_process(save_to_db=save_to_db, use_cache=use_cache)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro durante coleta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/summary', methods=['GET'])
def get_data_summary():
    """Obtém resumo dos dados mais recentes"""
    try:
        service = get_data_service()
        summary = service.get_latest_data_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Erro ao obter resumo: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/data/<data_type>', methods=['GET'])
def get_data_by_type(data_type):
    """Obtém dados por tipo específico"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 100)  # Máximo de 100 registros
        
        service = get_data_service()
        data = service.get_data_by_type(data_type, limit)
        
        return jsonify({
            'data_type': data_type,
            'limit': limit,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do tipo {data_type}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/history', methods=['GET'])
def get_collection_history():
    """Obtém histórico de coletas"""
    try:
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Máximo de 100 registros
        
        service = get_data_service()
        history = service.get_collection_history(limit)
        
        return jsonify({
            'limit': limit,
            'count': len(history),
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/apis/status', methods=['GET'])
def get_apis_status():
    """Obtém status atual das APIs"""
    try:
        service = get_data_service()
        status = service.get_apis_status()
        
        # Calcula estatísticas
        total_apis = len(status)
        online_apis = sum(1 for api in status if api['is_online'])
        offline_apis = total_apis - online_apis
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_apis': total_apis,
                'online_apis': online_apis,
                'offline_apis': offline_apis,
                'availability_percentage': (online_apis / max(total_apis, 1)) * 100
            },
            'apis': status
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar status das APIs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/auto-collection/start', methods=['POST'])
def start_auto_collection():
    """Inicia coleta automática"""
    try:
        service = get_data_service()
        success = service.start_auto_collection()
        
        if success:
            return jsonify({
                'message': 'Coleta automática iniciada com sucesso',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'Falha ao iniciar coleta automática'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao iniciar coleta automática: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/auto-collection/stop', methods=['POST'])
def stop_auto_collection():
    """Para coleta automática"""
    try:
        service = get_data_service()
        success = service.stop_auto_collection()
        
        if success:
            return jsonify({
                'message': 'Coleta automática parada com sucesso',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'Falha ao parar coleta automática'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao parar coleta automática: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """Obtém estatísticas do cache"""
    try:
        service = get_data_service()
        stats = service.storage.get_storage_stats()
        
        cache_stats = {
            'cache_entries': stats.get('cache_entries', 0),
            'cache_hit_rate': stats.get('cache_hit_rate', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(cache_stats)
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do cache: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Limpa cache (implementação futura)"""
    try:
        # Por enquanto, retorna mensagem informativa
        return jsonify({
            'message': 'Funcionalidade de limpeza de cache será implementada',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/logs', methods=['GET'])
def get_system_logs():
    """Obtém logs do sistema"""
    try:
        level = request.args.get('level')
        component = request.args.get('component')
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 200)  # Máximo de 200 logs
        
        service = get_data_service()
        logs = service.storage.get_logs(level=level, component=component, limit=limit)
        
        return jsonify({
            'filters': {
                'level': level,
                'component': component,
                'limit': limit
            },
            'count': len(logs),
            'logs': logs
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@data_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    try:
        service = get_data_service()
        
        # Verifica componentes principais
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'components': {
                'collector': bool(service.collector),
                'processor': bool(service.processor),
                'storage': bool(service.storage),
                'auto_collection': service.is_running
            },
            'version': '1.0.0'
        }
        
        # Verifica se todos os componentes estão funcionais
        all_healthy = all(health_status['components'].values())
        if not all_healthy:
            health_status['status'] = 'degraded'
        
        status_code = 200 if all_healthy else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@data_bp.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@data_bp.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    return jsonify({'error': 'Erro interno do servidor'}), 500

