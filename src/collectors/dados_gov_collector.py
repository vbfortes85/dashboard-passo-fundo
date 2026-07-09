"""
Módulo de coleta de dados do Portal Brasileiro de Dados Abertos (dados.gov.br)
Coleta datasets governamentais relacionados ao município
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

class DadosGovCollector:
    """Coletor de dados da API do Portal Brasileiro de Dados Abertos"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.base_url = "https://dados.gov.br/dados/api/publico"
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Termos de busca relacionados a Passo Fundo
        self.search_terms = [
            "Passo Fundo",
            "Rio Grande do Sul",
            "RS",
            "municipal",
            "município"
        ]
        
        # Organizações importantes
        self.important_orgs = [
            "ibge",
            "ministerio-da-saude",
            "ministerio-da-educacao",
            "ministerio-do-desenvolvimento-regional"
        ]
        
        self.headers = {
            'User-Agent': 'Dashboard-Passo-Fundo/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
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
    
    def search_datasets(self, termo_busca: str, pagina: int = 1, 
                       dados_abertos: bool = True) -> Optional[Dict]:
        """
        Busca datasets por termo
        
        Args:
            termo_busca: Termo para buscar nos datasets
            pagina: Número da página para paginação
            dados_abertos: Filtrar apenas dados abertos
        """
        url = f"{self.base_url}/conjuntos-dados"
        params = {
            'nomeConjuntoDados': termo_busca,
            'dadosAbertos': str(dados_abertos).lower(),
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'busca_datasets',
                'termo_busca': termo_busca,
                'pagina': pagina,
                'dados_abertos': dados_abertos,
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict]:
        """
        Obtém detalhes de um dataset específico
        
        Args:
            dataset_id: ID do dataset
        """
        url = f"{self.base_url}/conjuntos-dados/{dataset_id}"
        
        data = self._make_request(url)
        if data:
            return {
                'tipo': 'detalhes_dataset',
                'dataset_id': dataset_id,
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def get_organizations(self) -> Optional[Dict]:
        """Obtém lista de organizações disponíveis"""
        url = f"{self.base_url}/organizacao"
        
        data = self._make_request(url)
        if data:
            return {
                'tipo': 'organizacoes',
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def get_organization_details(self, org_id: str) -> Optional[Dict]:
        """
        Obtém detalhes de uma organização específica
        
        Args:
            org_id: ID da organização
        """
        url = f"{self.base_url}/organizacao/{org_id}"
        
        data = self._make_request(url)
        if data:
            return {
                'tipo': 'detalhes_organizacao',
                'organizacao_id': org_id,
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def get_themes(self) -> Optional[Dict]:
        """Obtém lista de temas disponíveis"""
        url = f"{self.base_url}/../temas"  # Endpoint está em nível diferente
        
        data = self._make_request(url)
        if data:
            return {
                'tipo': 'temas',
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def search_datasets_by_organization(self, org_id: str, pagina: int = 1) -> Optional[Dict]:
        """
        Busca datasets de uma organização específica
        
        Args:
            org_id: ID da organização
            pagina: Número da página para paginação
        """
        url = f"{self.base_url}/conjuntos-dados"
        params = {
            'idOrganizacao': org_id,
            'dadosAbertos': 'true',
            'pagina': pagina
        }
        
        data = self._make_request(url, params)
        if data:
            return {
                'tipo': 'datasets_organizacao',
                'organizacao_id': org_id,
                'pagina': pagina,
                'data_coleta': datetime.now().isoformat(),
                'dados': data
            }
        return None
    
    def search_municipal_datasets(self) -> Dict[str, Any]:
        """Busca datasets relacionados a dados municipais"""
        results = {}
        
        for termo in self.search_terms:
            try:
                self.logger.info(f"Buscando datasets para termo: {termo}")
                data = self.search_datasets(termo, pagina=1)
                if data:
                    results[f"busca_{termo.lower().replace(' ', '_')}"] = data
                
                # Pequena pausa entre buscas para evitar rate limit
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar datasets para '{termo}': {str(e)}")
        
        return results
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com a API do Dados.gov.br"""
        results = {
            'api_dados_gov': False,
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Teste com endpoint de temas (geralmente mais estável)
            url = f"{self.base_url}/../temas"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                results['api_dados_gov'] = True
            else:
                results['errors'].append(f"API Dados.gov.br: HTTP {response.status_code}")
                
        except Exception as e:
            results['errors'].append(f"API Dados.gov.br: {str(e)}")
        
        return results
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Coleta todos os dados disponíveis do Dados.gov.br"""
        self.logger.info("Iniciando coleta completa de dados do Dados.gov.br")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'organizacoes': None,
            'temas': None,
            'datasets_municipais': None,
            'datasets_ibge': None,
            'errors': [],
            'success': False
        }
        
        try:
            # Lista de organizações
            results['organizacoes'] = self.get_organizations()
            if not results['organizacoes']:
                results['errors'].append("Falha ao obter lista de organizações")
            
            # Lista de temas
            results['temas'] = self.get_themes()
            if not results['temas']:
                results['errors'].append("Falha ao obter lista de temas")
            
            # Busca datasets municipais
            datasets_municipais = self.search_municipal_datasets()
            if datasets_municipais:
                results['datasets_municipais'] = {
                    'tipo': 'datasets_municipais_agregados',
                    'data_coleta': datetime.now().isoformat(),
                    'buscas': datasets_municipais
                }
            else:
                results['errors'].append("Falha ao obter datasets municipais")
            
            # Datasets do IBGE (se disponível)
            try:
                results['datasets_ibge'] = self.search_datasets_by_organization('ibge', pagina=1)
                if not results['datasets_ibge']:
                    results['errors'].append("Falha ao obter datasets do IBGE")
            except Exception as e:
                results['errors'].append(f"Erro ao buscar datasets do IBGE: {str(e)}")
            
            # Determina sucesso baseado na quantidade de dados coletados
            successful_collections = sum([
                1 for key in ['organizacoes', 'temas', 'datasets_municipais', 'datasets_ibge'] 
                if results[key] is not None
            ])
            
            results['success'] = successful_collections >= 2  # Pelo menos 2 de 4 coletas bem-sucedidas
            
            self.logger.info(f"Coleta Dados.gov.br concluída. Sucessos: {successful_collections}/4")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta Dados.gov.br: {str(e)}")
            results['errors'].append(f"Erro geral: {str(e)}")
        
        return results


if __name__ == "__main__":
    # Teste do coletor
    logging.basicConfig(level=logging.INFO)
    collector = DadosGovCollector()
    
    print("=== Teste de Conectividade Dados.gov.br ===")
    connectivity = collector.test_connectivity()
    print(f"Conectividade: {connectivity}")
    
    print("\n=== Coleta Completa Dados.gov.br ===")
    data = collector.collect_all_data()
    print(f"Resultado: {data['success']}")
    print(f"Erros: {data['errors']}")

