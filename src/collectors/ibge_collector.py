"""
Módulo de coleta de dados do IBGE
Coleta dados demográficos e econômicos municipais
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

class IBGECollector:
    """Coletor de dados da API do IBGE"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.base_url_localidades = "https://servicodados.ibge.gov.br/api/v1/localidades"
        self.base_url_agregados = "https://servicodados.ibge.gov.br/api/v3/agregados"
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Códigos importantes
        self.passo_fundo_id = "4314902"
        self.rs_id = "43"
        
        # Agregados importantes
        self.agregados = {
            "populacao": 1705,  # Estimativas da população
            "pib_municipal": 5938,  # PIB dos municípios
            "pib_per_capita": 5938  # PIB per capita
        }
        
        self.headers = {
            'User-Agent': 'Dashboard-Passo-Fundo/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Faz requisição HTTP com retry e tratamento de erros"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Fazendo requisição para: {url} (tentativa {attempt + 1})")
                response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
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
    
    def get_municipio_info(self) -> Optional[Dict]:
        """Obtém informações básicas do município de Passo Fundo"""
        url = f"{self.base_url_localidades}/municipios/{self.passo_fundo_id}"
        return self._make_request(url)
    
    def get_populacao_estimada(self, ano: Optional[int] = None) -> Optional[Dict]:
        """Obtém estimativa populacional de Passo Fundo"""
        # Se não especificar ano, pega o último disponível
        periodo = f"-1" if ano is None else str(ano)
        
        url = f"{self.base_url_agregados}/{self.agregados['populacao']}/periodos/{periodo}/variaveis/allxp"
        params = {
            'localidades': f"N6[{self.passo_fundo_id}]"
        }
        
        data = self._make_request(url, params)
        if data:
            return self._process_agregado_data(data, "população")
        return None
    
    def get_pib_municipal(self, ano: Optional[int] = None) -> Optional[Dict]:
        """Obtém dados do PIB municipal de Passo Fundo"""
        periodo = f"-1" if ano is None else str(ano)
        
        url = f"{self.base_url_agregados}/{self.agregados['pib_municipal']}/periodos/{periodo}/variaveis/allxp"
        params = {
            'localidades': f"N6[{self.passo_fundo_id}]"
        }
        
        data = self._make_request(url, params)
        if data:
            return self._process_agregado_data(data, "pib_municipal")
        return None
    
    def get_municipios_rs(self) -> Optional[List[Dict]]:
        """Obtém lista de todos os municípios do RS"""
        url = f"{self.base_url_localidades}/estados/{self.rs_id}/municipios"
        params = {'orderBy': 'nome'}
        return self._make_request(url, params)
    
    def _process_agregado_data(self, data: List[Dict], tipo: str) -> Dict:
        """Processa dados de agregados do IBGE"""
        processed_data = {
            'tipo': tipo,
            'municipio': 'Passo Fundo',
            'codigo_ibge': self.passo_fundo_id,
            'data_coleta': datetime.now().isoformat(),
            'dados': []
        }
        
        for item in data:
            if 'resultados' in item:
                for resultado in item['resultados']:
                    for serie in resultado.get('series', []):
                        localidade = serie.get('localidade', {})
                        if localidade.get('id') == int(self.passo_fundo_id):
                            processed_data['dados'].append({
                                'variavel': resultado.get('variavel'),
                                'unidade': resultado.get('unidade'),
                                'valores': serie.get('serie', {})
                            })
        
        return processed_data
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com a API do IBGE"""
        results = {
            'api_localidades': False,
            'api_agregados': False,
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        # Teste API de Localidades
        try:
            url = f"{self.base_url_localidades}/municipios/{self.passo_fundo_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            results['api_localidades'] = response.status_code == 200
            if response.status_code != 200:
                results['errors'].append(f"API Localidades: HTTP {response.status_code}")
        except Exception as e:
            results['errors'].append(f"API Localidades: {str(e)}")
        
        # Teste API de Agregados
        try:
            url = f"{self.base_url_agregados}/{self.agregados['populacao']}/metadados"
            response = requests.get(url, headers=self.headers, timeout=10)
            results['api_agregados'] = response.status_code == 200
            if response.status_code != 200:
                results['errors'].append(f"API Agregados: HTTP {response.status_code}")
        except Exception as e:
            results['errors'].append(f"API Agregados: {str(e)}")
        
        return results
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Coleta todos os dados disponíveis do IBGE para Passo Fundo"""
        self.logger.info("Iniciando coleta completa de dados do IBGE")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'municipio_info': None,
            'populacao': None,
            'pib_municipal': None,
            'errors': [],
            'success': False
        }
        
        try:
            # Informações básicas do município
            results['municipio_info'] = self.get_municipio_info()
            if not results['municipio_info']:
                results['errors'].append("Falha ao obter informações básicas do município")
            
            # População estimada
            results['populacao'] = self.get_populacao_estimada()
            if not results['populacao']:
                results['errors'].append("Falha ao obter dados de população")
            
            # PIB municipal
            results['pib_municipal'] = self.get_pib_municipal()
            if not results['pib_municipal']:
                results['errors'].append("Falha ao obter dados de PIB municipal")
            
            # Determina sucesso baseado na quantidade de dados coletados
            successful_collections = sum([
                1 for key in ['municipio_info', 'populacao', 'pib_municipal'] 
                if results[key] is not None
            ])
            
            results['success'] = successful_collections >= 2  # Pelo menos 2 de 3 coletas bem-sucedidas
            
            self.logger.info(f"Coleta IBGE concluída. Sucessos: {successful_collections}/3")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta IBGE: {str(e)}")
            results['errors'].append(f"Erro geral: {str(e)}")
        
        return results


if __name__ == "__main__":
    # Teste do coletor
    logging.basicConfig(level=logging.INFO)
    collector = IBGECollector()
    
    print("=== Teste de Conectividade IBGE ===")
    connectivity = collector.test_connectivity()
    print(f"Conectividade: {connectivity}")
    
    print("\n=== Coleta Completa IBGE ===")
    data = collector.collect_all_data()
    print(f"Resultado: {data['success']}")
    print(f"Erros: {data['errors']}")

