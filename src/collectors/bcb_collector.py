"""
Módulo de coleta de dados do Banco Central do Brasil (BCB)
Coleta indicadores econômicos nacionais via API SGS
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

class BCBCollector:
    """Coletor de dados da API do Banco Central (SGS)"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.base_url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Séries importantes do SGS
        self.series = {
            "ipca": 433,  # IPCA - Índice de Preços ao Consumidor Amplo
            "selic": 432,  # Taxa Selic
            "selic_acumulada": 11,  # Taxa Selic acumulada no mês
            "pib_mensal": 4380,  # PIB mensal
            "igp_m": 189,  # IGP-M - Índice Geral de Preços do Mercado
            "cdi": 4391,  # CDI - Certificado de Depósito Interbancário
            "ibc_br": 24363,  # IBC-Br - Índice de Atividade Econômica do BC
            "dolar_compra": 1,  # Dólar comercial - cotação de compra
            "dolar_venda": 10813,  # Dólar comercial - cotação de venda
        }
        
        self.headers = {
            'User-Agent': 'Dashboard-Passo-Fundo/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[List[Dict]]:
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
    
    def get_serie_data(self, serie_code: int, data_inicial: Optional[str] = None, 
                      data_final: Optional[str] = None, ultimos_n: Optional[int] = None) -> Optional[Dict]:
        """
        Obtém dados de uma série temporal do BCB
        
        Args:
            serie_code: Código da série no SGS
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            ultimos_n: Número de últimos valores a retornar
        """
        if ultimos_n:
            url = f"{self.base_url}.{serie_code}/dados/ultimos/{ultimos_n}"
            params = {'formato': 'json'}
        else:
            url = f"{self.base_url}.{serie_code}/dados"
            params = {'formato': 'json'}
            if data_inicial:
                params['dataInicial'] = data_inicial
            if data_final:
                params['dataFinal'] = data_final
        
        data = self._make_request(url, params)
        if data:
            return {
                'serie_code': serie_code,
                'data_coleta': datetime.now().isoformat(),
                'parametros': {
                    'data_inicial': data_inicial,
                    'data_final': data_final,
                    'ultimos_n': ultimos_n
                },
                'dados': data
            }
        return None
    
    def get_ipca_ultimos_12_meses(self) -> Optional[Dict]:
        """Obtém IPCA dos últimos 12 meses"""
        return self.get_serie_data(self.series['ipca'], ultimos_n=12)
    
    def get_selic_atual(self) -> Optional[Dict]:
        """Obtém taxa Selic atual (último valor)"""
        return self.get_serie_data(self.series['selic'], ultimos_n=1)
    
    def get_selic_ano_atual(self) -> Optional[Dict]:
        """Obtém taxa Selic do ano atual (últimos 12 valores)"""
        return self.get_serie_data(self.series['selic'], ultimos_n=12)
    
    def get_dolar_ultimos_30_dias(self) -> Optional[Dict]:
        """Obtém cotação do dólar dos últimos 20 dias (limite da API)"""
        return self.get_serie_data(self.series['dolar_compra'], ultimos_n=20)
    
    def get_ibc_br_ultimos_12_meses(self) -> Optional[Dict]:
        """Obtém IBC-Br dos últimos 12 meses"""
        return self.get_serie_data(self.series['ibc_br'], ultimos_n=12)
    
    def get_igp_m_ultimos_12_meses(self) -> Optional[Dict]:
        """Obtém IGP-M dos últimos 12 meses"""
        return self.get_serie_data(self.series['igp_m'], ultimos_n=12)
    
    def get_indicadores_periodo(self, data_inicial: str, data_final: str) -> Dict[str, Any]:
        """
        Obtém múltiplos indicadores para um período específico
        
        Args:
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
        """
        indicadores = {}
        
        # Lista de indicadores principais para coletar
        principais_series = {
            'ipca': self.series['ipca'],
            'selic': self.series['selic'],
            'dolar_compra': self.series['dolar_compra'],
            'igp_m': self.series['igp_m'],
            'ibc_br': self.series['ibc_br']
        }
        
        for nome, codigo in principais_series.items():
            try:
                data = self.get_serie_data(codigo, data_inicial, data_final)
                if data:
                    indicadores[nome] = data
                else:
                    self.logger.warning(f"Falha ao obter dados da série {nome} ({codigo})")
            except Exception as e:
                self.logger.error(f"Erro ao coletar série {nome}: {str(e)}")
        
        return indicadores
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com a API do BCB"""
        results = {
            'api_sgs': False,
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Teste com série IPCA (mais estável)
            url = f"{self.base_url}.{self.series['ipca']}/dados/ultimos/1"
            params = {'formato': 'json'}
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            results['api_sgs'] = response.status_code == 200
            if response.status_code != 200:
                results['errors'].append(f"API SGS: HTTP {response.status_code}")
            else:
                # Verifica se retornou dados válidos
                data = response.json()
                if not data or not isinstance(data, list):
                    results['api_sgs'] = False
                    results['errors'].append("API SGS: Resposta inválida")
                    
        except Exception as e:
            results['errors'].append(f"API SGS: {str(e)}")
        
        return results
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Coleta todos os indicadores econômicos importantes"""
        self.logger.info("Iniciando coleta completa de dados do BCB")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'ipca_12m': None,
            'selic_atual': None,
            'selic_ano': None,
            'dolar_30d': None,
            'ibc_br_12m': None,
            'igp_m_12m': None,
            'errors': [],
            'success': False
        }
        
        try:
            # IPCA últimos 12 meses
            results['ipca_12m'] = self.get_ipca_ultimos_12_meses()
            if not results['ipca_12m']:
                results['errors'].append("Falha ao obter IPCA")
            
            # Selic atual
            results['selic_atual'] = self.get_selic_atual()
            if not results['selic_atual']:
                results['errors'].append("Falha ao obter Selic atual")
            
            # Selic do ano
            results['selic_ano'] = self.get_selic_ano_atual()
            if not results['selic_ano']:
                results['errors'].append("Falha ao obter Selic do ano")
            
            # Dólar últimos 30 dias
            results['dolar_30d'] = self.get_dolar_ultimos_30_dias()
            if not results['dolar_30d']:
                results['errors'].append("Falha ao obter cotação do dólar")
            
            # IBC-Br últimos 12 meses
            results['ibc_br_12m'] = self.get_ibc_br_ultimos_12_meses()
            if not results['ibc_br_12m']:
                results['errors'].append("Falha ao obter IBC-Br")
            
            # IGP-M últimos 12 meses
            results['igp_m_12m'] = self.get_igp_m_ultimos_12_meses()
            if not results['igp_m_12m']:
                results['errors'].append("Falha ao obter IGP-M")
            
            # Determina sucesso baseado na quantidade de dados coletados
            successful_collections = sum([
                1 for key in ['ipca_12m', 'selic_atual', 'selic_ano', 'dolar_30d', 'ibc_br_12m', 'igp_m_12m'] 
                if results[key] is not None
            ])
            
            results['success'] = successful_collections >= 4  # Pelo menos 4 de 6 coletas bem-sucedidas
            
            self.logger.info(f"Coleta BCB concluída. Sucessos: {successful_collections}/6")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta BCB: {str(e)}")
            results['errors'].append(f"Erro geral: {str(e)}")
        
        return results


if __name__ == "__main__":
    # Teste do coletor
    logging.basicConfig(level=logging.INFO)
    collector = BCBCollector()
    
    print("=== Teste de Conectividade BCB ===")
    connectivity = collector.test_connectivity()
    print(f"Conectividade: {connectivity}")
    
    print("\n=== Coleta Completa BCB ===")
    data = collector.collect_all_data()
    print(f"Resultado: {data['success']}")
    print(f"Erros: {data['errors']}")

