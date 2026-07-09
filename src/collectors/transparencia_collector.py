"""
Módulo de coleta de dados do Portal da Transparência
Coleta contratos e convênios federais
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

class TransparenciaCollector:
    """Coletor de dados da API do Portal da Transparência"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, api_key: Optional[str] = None):
        self.base_url = "https://api.portaldatransparencia.gov.br/api-de-dados"
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        
        # Códigos importantes
        self.passo_fundo_ibge = "4314902"
        self.rs_uf = "RS"
        
        self.headers = {
            'User-Agent': 'Dashboard-Passo-Fundo/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Adiciona chave de API se fornecida
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Faz requisição HTTP com retry e tratamento de erros"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Fazendo requisição para: {url} (tentativa {attempt + 1})")
                response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    self.logger.error("Erro de autenticação - chave de API inválida ou ausente")
                    return None
                elif response.status_code == 429:
                    # Rate limit - aguardar antes de tentar novamente
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Rate limit atingido. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Erro HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"Timeout na requisição (tentativa {attempt + 1})")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Erro na requisição: {str(e)} (tentativa {attempt + 1})")
            
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        
        return None
    
    def get_convenios_municipio(self, data_inicial: str, data_final: str, 
                               pagina: int = 1) -> Optional[Dict]:
        """
        Obtém convênios do município de Passo Fundo
        
        Args:
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            pagina: Número da página para paginação
        """
        url = f"{self.base_url}/convenios"
        params = {
            'codigoIBGE': self.passo_fundo_ibge,
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'convenios_municipio',
                'municipio': 'Passo Fundo',
                'codigo_ibge': self.passo_fundo_ibge,
                'periodo': f"{data_inicial} a {data_final}",
                'data_coleta': datetime.now().isoformat(),
                'pagina': pagina,
                'dados': data
            }
        return None
    
    def get_convenios_estado(self, data_inicial: str, data_final: str, 
                            pagina: int = 1) -> Optional[Dict]:
        """
        Obtém convênios do estado do Rio Grande do Sul
        
        Args:
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            pagina: Número da página para paginação
        """
        url = f"{self.base_url}/convenios"
        params = {
            'uf': self.rs_uf,
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'convenios_estado',
                'estado': 'Rio Grande do Sul',
                'uf': self.rs_uf,
                'periodo': f"{data_inicial} a {data_final}",
                'data_coleta': datetime.now().isoformat(),
                'pagina': pagina,
                'dados': data
            }
        return None
    
    def get_licitacoes(self, data_inicial: str, data_final: str, 
                      pagina: int = 1) -> Optional[Dict]:
        """
        Obtém licitações federais
        
        Args:
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            pagina: Número da página para paginação
        """
        url = f"{self.base_url}/licitacoes"
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'licitacoes_federais',
                'periodo': f"{data_inicial} a {data_final}",
                'data_coleta': datetime.now().isoformat(),
                'pagina': pagina,
                'dados': data
            }
        return None
    
    def get_tipos_instrumento(self) -> Optional[Dict]:
        """Obtém tipos de instrumentos usados nos convênios"""
        url = f"{self.base_url}/convenios/tipo-instrumento"
        
        data = self._make_request(url)
        if data:
            return {
                'tipo': 'tipos_instrumento',
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def get_despesas_municipio(self, data_inicial: str, data_final: str,
                              pagina: int = 1) -> Optional[Dict]:
        """
        Obtém despesas relacionadas ao município
        
        Args:
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            pagina: Número da página para paginação
        """
        url = f"{self.base_url}/despesas/documentos"
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'despesas_federais',
                'periodo': f"{data_inicial} a {data_final}",
                'data_coleta': datetime.now().isoformat(),
                'pagina': pagina,
                'dados': data
            }
        return None
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com a API do Portal da Transparência"""
        results = {
            'api_transparencia': False,
            'requires_auth': False,
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Teste com endpoint de tipos de instrumento (geralmente público)
            url = f"{self.base_url}/convenios/tipo-instrumento"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                results['api_transparencia'] = True
            elif response.status_code == 401:
                results['requires_auth'] = True
                results['errors'].append("API requer autenticação - chave de API necessária")
            else:
                results['errors'].append(f"API Transparência: HTTP {response.status_code}")
                
        except Exception as e:
            results['errors'].append(f"API Transparência: {str(e)}")
        
        return results
    
    def collect_all_data(self, ano: Optional[int] = None) -> Dict[str, Any]:
        """
        Coleta todos os dados disponíveis do Portal da Transparência
        
        Args:
            ano: Ano para coleta (padrão: ano atual)
        """
        if ano is None:
            ano = datetime.now().year
        
        data_inicial = f"01/01/{ano}"
        data_final = f"31/12/{ano}"
        
        self.logger.info(f"Iniciando coleta completa de dados do Portal da Transparência para {ano}")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'ano': ano,
            'convenios_municipio': None,
            'convenios_estado': None,
            'tipos_instrumento': None,
            'licitacoes': None,
            'errors': [],
            'success': False,
            'auth_required': False
        }
        
        try:
            # Tipos de instrumento (não requer filtros específicos)
            results['tipos_instrumento'] = self.get_tipos_instrumento()
            if not results['tipos_instrumento']:
                results['errors'].append("Falha ao obter tipos de instrumento")
            
            # Convênios do município
            results['convenios_municipio'] = self.get_convenios_municipio(data_inicial, data_final)
            if not results['convenios_municipio']:
                results['errors'].append("Falha ao obter convênios do município")
            
            # Convênios do estado
            results['convenios_estado'] = self.get_convenios_estado(data_inicial, data_final)
            if not results['convenios_estado']:
                results['errors'].append("Falha ao obter convênios do estado")
            
            # Licitações federais (amostra limitada)
            results['licitacoes'] = self.get_licitacoes(data_inicial, data_final)
            if not results['licitacoes']:
                results['errors'].append("Falha ao obter licitações federais")
            
            # Verifica se houve erro de autenticação
            auth_errors = [error for error in results['errors'] if 'autenticação' in error.lower()]
            if auth_errors:
                results['auth_required'] = True
            
            # Determina sucesso baseado na quantidade de dados coletados
            successful_collections = sum([
                1 for key in ['convenios_municipio', 'convenios_estado', 'tipos_instrumento', 'licitacoes'] 
                if results[key] is not None
            ])
            
            # Se pelo menos tipos_instrumento foi coletado, considera parcialmente bem-sucedido
            results['success'] = successful_collections >= 1
            
            self.logger.info(f"Coleta Portal da Transparência concluída. Sucessos: {successful_collections}/4")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta Portal da Transparência: {str(e)}")
            results['errors'].append(f"Erro geral: {str(e)}")
        
        return results


if __name__ == "__main__":
    # Teste do coletor
    logging.basicConfig(level=logging.INFO)
    collector = TransparenciaCollector()
    
    print("=== Teste de Conectividade Portal da Transparência ===")
    connectivity = collector.test_connectivity()
    print(f"Conectividade: {connectivity}")
    
    print("\n=== Coleta Completa Portal da Transparência ===")
    data = collector.collect_all_data()
    print(f"Resultado: {data['success']}")
    print(f"Erros: {data['errors']}")
    print(f"Requer autenticação: {data['auth_required']}")

