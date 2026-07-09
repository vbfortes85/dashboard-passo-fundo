"""
Processador de dados coletados das APIs governamentais
Normaliza, valida e processa dados para armazenamento e visualização
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
import re
from decimal import Decimal, InvalidOperation

class DataProcessor:
    """Processador principal de dados coletados"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapeamentos de normalização
        self.data_type_mappings = {
            'ibge': {
                'municipio_info': 'municipal_info',
                'populacao': 'population_data',
                'pib_municipal': 'municipal_gdp'
            },
            'bcb': {
                'ipca_12m': 'inflation_ipca',
                'selic_atual': 'interest_rate_selic',
                'selic_ano': 'interest_rate_selic_yearly',
                'dolar_30d': 'exchange_rate_usd',
                'ibc_br_12m': 'economic_activity_index',
                'igp_m_12m': 'inflation_igp_m'
            },
            'transparencia': {
                'convenios_municipio': 'federal_agreements_municipal',
                'convenios_estado': 'federal_agreements_state',
                'tipos_instrumento': 'agreement_types',
                'licitacoes': 'federal_bids'
            },
            'dados_gov': {
                'datasets_municipais': 'municipal_datasets',
                'organizacoes': 'government_organizations',
                'temas': 'data_themes'
            }
        }
    
    def process_collection_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa resultados completos de uma coleta
        
        Args:
            results: Resultados da coleta do MainCollector
            
        Returns:
            Dados processados e normalizados
        """
        processed_results = {
            'timestamp': datetime.now().isoformat(),
            'original_timestamp': results.get('timestamp'),
            'execution_mode': results.get('execution_mode'),
            'summary': results.get('summary', {}),
            'processed_sources': {},
            'aggregated_data': {},
            'quality_metrics': {}
        }
        
        # Processa cada fonte
        for source_name, source_data in results.get('sources', {}).items():
            try:
                processed_source = self.process_source_data(source_name, source_data)
                processed_results['processed_sources'][source_name] = processed_source
                
                # Adiciona dados processados ao agregado
                if processed_source.get('success') and processed_source.get('normalized_data'):
                    self._merge_to_aggregated(
                        processed_results['aggregated_data'],
                        processed_source['normalized_data']
                    )
                
            except Exception as e:
                self.logger.error(f"Erro ao processar fonte {source_name}: {str(e)}")
                processed_results['processed_sources'][source_name] = {
                    'success': False,
                    'error': f"Erro no processamento: {str(e)}"
                }
        
        # Calcula métricas de qualidade
        processed_results['quality_metrics'] = self._calculate_quality_metrics(processed_results)
        
        return processed_results
    
    def process_source_data(self, source_name: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa dados de uma fonte específica
        
        Args:
            source_name: Nome da fonte (ibge, bcb, transparencia, dados_gov)
            source_data: Dados brutos da fonte
            
        Returns:
            Dados processados da fonte
        """
        processed = {
            'source': source_name,
            'success': source_data.get('success', False),
            'timestamp': source_data.get('timestamp'),
            'duration_seconds': source_data.get('duration_seconds', 0),
            'normalized_data': {},
            'validation_errors': [],
            'processing_notes': []
        }
        
        if not processed['success']:
            processed['error'] = source_data.get('error', 'Coleta não foi bem-sucedida')
            return processed
        
        # Processa dados específicos por fonte
        raw_data = source_data.get('data', {})
        
        if source_name == 'ibge':
            processed['normalized_data'] = self._process_ibge_data(raw_data)
        elif source_name == 'bcb':
            processed['normalized_data'] = self._process_bcb_data(raw_data)
        elif source_name == 'transparencia':
            processed['normalized_data'] = self._process_transparencia_data(raw_data)
        elif source_name == 'dados_gov':
            processed['normalized_data'] = self._process_dados_gov_data(raw_data)
        else:
            processed['validation_errors'].append(f"Fonte desconhecida: {source_name}")
        
        # Valida dados processados
        self._validate_processed_data(processed)
        
        return processed
    
    def _process_ibge_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do IBGE"""
        normalized = {}
        
        # Informações municipais
        if 'municipio_info' in data and data['municipio_info']:
            municipio = data['municipio_info']
            normalized['municipal_info'] = {
                'municipality_name': municipio.get('nome'),
                'ibge_code': municipio.get('id'),
                'state': municipio.get('microrregiao', {}).get('mesorregiao', {}).get('UF', {}).get('nome'),
                'state_code': municipio.get('microrregiao', {}).get('mesorregiao', {}).get('UF', {}).get('sigla'),
                'microregion': municipio.get('microrregiao', {}).get('nome'),
                'mesoregion': municipio.get('microrregiao', {}).get('mesorregiao', {}).get('nome'),
                'last_updated': datetime.now().isoformat()
            }
        
        # Dados de população
        if 'populacao' in data and data['populacao']:
            pop_data = data['populacao']
            if 'dados' in pop_data and pop_data['dados']:
                normalized['population_data'] = {
                    'data_type': 'population_estimate',
                    'municipality': pop_data.get('municipio'),
                    'ibge_code': pop_data.get('codigo_ibge'),
                    'collection_date': pop_data.get('data_coleta'),
                    'estimates': self._extract_population_values(pop_data['dados'])
                }
        
        # Dados de PIB
        if 'pib_municipal' in data and data['pib_municipal']:
            pib_data = data['pib_municipal']
            if 'dados' in pib_data and pib_data['dados']:
                normalized['municipal_gdp'] = {
                    'data_type': 'municipal_gdp',
                    'municipality': pib_data.get('municipio'),
                    'ibge_code': pib_data.get('codigo_ibge'),
                    'collection_date': pib_data.get('data_coleta'),
                    'gdp_values': self._extract_gdp_values(pib_data['dados'])
                }
        
        return normalized
    
    def _process_bcb_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do Banco Central"""
        normalized = {}
        
        # IPCA
        if 'ipca_12m' in data and data['ipca_12m']:
            ipca_data = data['ipca_12m']
            normalized['inflation_ipca'] = {
                'data_type': 'inflation_rate',
                'indicator': 'IPCA',
                'period': '12_months',
                'collection_date': ipca_data.get('data_coleta'),
                'values': self._extract_bcb_series_values(ipca_data.get('dados', []))
            }
        
        # Selic atual
        if 'selic_atual' in data and data['selic_atual']:
            selic_data = data['selic_atual']
            normalized['interest_rate_selic'] = {
                'data_type': 'interest_rate',
                'indicator': 'SELIC',
                'period': 'current',
                'collection_date': selic_data.get('data_coleta'),
                'values': self._extract_bcb_series_values(selic_data.get('dados', []))
            }
        
        # Dólar
        if 'dolar_30d' in data and data['dolar_30d']:
            dolar_data = data['dolar_30d']
            normalized['exchange_rate_usd'] = {
                'data_type': 'exchange_rate',
                'currency_pair': 'USD/BRL',
                'period': '30_days',
                'collection_date': dolar_data.get('data_coleta'),
                'values': self._extract_bcb_series_values(dolar_data.get('dados', []))
            }
        
        # IBC-Br
        if 'ibc_br_12m' in data and data['ibc_br_12m']:
            ibc_data = data['ibc_br_12m']
            normalized['economic_activity_index'] = {
                'data_type': 'economic_activity',
                'indicator': 'IBC-Br',
                'period': '12_months',
                'collection_date': ibc_data.get('data_coleta'),
                'values': self._extract_bcb_series_values(ibc_data.get('dados', []))
            }
        
        return normalized
    
    def _process_transparencia_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do Portal da Transparência"""
        normalized = {}
        
        # Convênios municipais
        if 'convenios_municipio' in data and data['convenios_municipio']:
            conv_data = data['convenios_municipio']
            normalized['federal_agreements_municipal'] = {
                'data_type': 'federal_agreements',
                'scope': 'municipal',
                'municipality': conv_data.get('municipio'),
                'ibge_code': conv_data.get('codigo_ibge'),
                'period': conv_data.get('periodo'),
                'collection_date': conv_data.get('data_coleta'),
                'agreements': self._extract_agreements_data(conv_data.get('dados', {}))
            }
        
        # Convênios estaduais
        if 'convenios_estado' in data and data['convenios_estado']:
            conv_data = data['convenios_estado']
            normalized['federal_agreements_state'] = {
                'data_type': 'federal_agreements',
                'scope': 'state',
                'state': conv_data.get('estado'),
                'uf': conv_data.get('uf'),
                'period': conv_data.get('periodo'),
                'collection_date': conv_data.get('data_coleta'),
                'agreements': self._extract_agreements_data(conv_data.get('dados', {}))
            }
        
        # Tipos de instrumento
        if 'tipos_instrumento' in data and data['tipos_instrumento']:
            tipos_data = data['tipos_instrumento']
            normalized['agreement_types'] = {
                'data_type': 'reference_data',
                'category': 'agreement_types',
                'collection_date': tipos_data.get('data_coleta'),
                'types': tipos_data.get('dados', [])
            }
        
        return normalized
    
    def _process_dados_gov_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do Dados.gov.br"""
        normalized = {}
        
        # Organizações
        if 'organizacoes' in data and data['organizacoes']:
            org_data = data['organizacoes']
            normalized['government_organizations'] = {
                'data_type': 'reference_data',
                'category': 'organizations',
                'collection_date': org_data.get('data_coleta'),
                'organizations': self._extract_organizations_data(org_data.get('dados', []))
            }
        
        # Temas
        if 'temas' in data and data['temas']:
            temas_data = data['temas']
            normalized['data_themes'] = {
                'data_type': 'reference_data',
                'category': 'themes',
                'collection_date': temas_data.get('data_coleta'),
                'themes': temas_data.get('dados', [])
            }
        
        # Datasets municipais
        if 'datasets_municipais' in data and data['datasets_municipais']:
            datasets_data = data['datasets_municipais']
            normalized['municipal_datasets'] = {
                'data_type': 'datasets_catalog',
                'scope': 'municipal',
                'collection_date': datasets_data.get('data_coleta'),
                'searches': self._extract_datasets_data(datasets_data.get('buscas', {}))
            }
        
        return normalized
    
    def _extract_population_values(self, dados: List[Dict]) -> List[Dict]:
        """Extrai valores de população dos dados do IBGE"""
        values = []
        for item in dados:
            if 'valores' in item:
                for year, value in item['valores'].items():
                    try:
                        values.append({
                            'year': int(year),
                            'value': int(value) if value != '-' else None,
                            'variable': item.get('variavel'),
                            'unit': item.get('unidade')
                        })
                    except (ValueError, TypeError):
                        continue
        return sorted(values, key=lambda x: x['year'], reverse=True)
    
    def _extract_gdp_values(self, dados: List[Dict]) -> List[Dict]:
        """Extrai valores de PIB dos dados do IBGE"""
        values = []
        for item in dados:
            if 'valores' in item:
                for year, value in item['valores'].items():
                    try:
                        # PIB geralmente vem em milhares de reais
                        numeric_value = float(value) if value != '-' else None
                        values.append({
                            'year': int(year),
                            'value': numeric_value,
                            'variable': item.get('variavel'),
                            'unit': item.get('unidade')
                        })
                    except (ValueError, TypeError):
                        continue
        return sorted(values, key=lambda x: x['year'], reverse=True)
    
    def _extract_bcb_series_values(self, dados: List[Dict]) -> List[Dict]:
        """Extrai valores de séries temporais do BCB"""
        values = []
        for item in dados:
            try:
                # Converte data do formato DD/MM/AAAA
                date_str = item.get('data', '')
                if date_str:
                    date_parts = date_str.split('/')
                    if len(date_parts) == 3:
                        date_obj = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                    else:
                        date_obj = None
                else:
                    date_obj = None
                
                # Converte valor
                value_str = item.get('valor', '')
                try:
                    numeric_value = float(value_str) if value_str else None
                except (ValueError, TypeError):
                    numeric_value = None
                
                values.append({
                    'date': date_obj.isoformat() if date_obj else None,
                    'date_str': date_str,
                    'value': numeric_value,
                    'value_str': value_str
                })
            except Exception:
                continue
        
        return sorted(values, key=lambda x: x['date'] or '', reverse=True)
    
    def _extract_agreements_data(self, dados: Dict) -> Dict[str, Any]:
        """Extrai dados de convênios do Portal da Transparência"""
        if not isinstance(dados, dict):
            return {'raw_data': dados, 'processed': False}
        
        return {
            'total_records': dados.get('totalRecords', 0),
            'page_info': {
                'current_page': dados.get('currentPage', 1),
                'total_pages': dados.get('totalPages', 1),
                'page_size': dados.get('pageSize', 0)
            },
            'agreements': dados.get('data', []),
            'processed': True
        }
    
    def _extract_organizations_data(self, dados: List) -> List[Dict]:
        """Extrai dados de organizações do Dados.gov.br"""
        organizations = []
        for org in dados:
            if isinstance(org, dict):
                organizations.append({
                    'id': org.get('id'),
                    'name': org.get('name'),
                    'title': org.get('title'),
                    'description': org.get('description'),
                    'type': org.get('type'),
                    'state': org.get('state')
                })
        return organizations
    
    def _extract_datasets_data(self, buscas: Dict) -> Dict[str, Any]:
        """Extrai dados de datasets do Dados.gov.br"""
        processed_searches = {}
        for search_key, search_data in buscas.items():
            if isinstance(search_data, dict) and 'dados' in search_data:
                processed_searches[search_key] = {
                    'search_term': search_data.get('termo_busca'),
                    'total_results': len(search_data.get('dados', [])),
                    'datasets': search_data.get('dados', [])
                }
        return processed_searches
    
    def _merge_to_aggregated(self, aggregated: Dict, normalized_data: Dict) -> None:
        """Mescla dados normalizados ao agregado geral"""
        for key, value in normalized_data.items():
            if key not in aggregated:
                aggregated[key] = []
            aggregated[key].append(value)
    
    def _validate_processed_data(self, processed: Dict[str, Any]) -> None:
        """Valida dados processados"""
        normalized_data = processed.get('normalized_data', {})
        
        # Verifica se há dados normalizados
        if not normalized_data:
            processed['validation_errors'].append("Nenhum dado foi normalizado")
            return
        
        # Valida estrutura de cada tipo de dado
        for data_type, data_content in normalized_data.items():
            if not isinstance(data_content, dict):
                processed['validation_errors'].append(f"Dados de {data_type} não são um dicionário")
                continue
            
            # Verifica campos obrigatórios
            required_fields = ['data_type', 'collection_date']
            for field in required_fields:
                if field not in data_content:
                    processed['validation_errors'].append(f"Campo obrigatório '{field}' ausente em {data_type}")
            
            # Valida data de coleta
            if 'collection_date' in data_content:
                try:
                    datetime.fromisoformat(data_content['collection_date'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    processed['validation_errors'].append(f"Data de coleta inválida em {data_type}")
    
    def _calculate_quality_metrics(self, processed_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas de qualidade dos dados processados"""
        metrics = {
            'total_sources': len(processed_results.get('processed_sources', {})),
            'successful_sources': 0,
            'sources_with_data': 0,
            'total_validation_errors': 0,
            'data_completeness': {},
            'processing_success_rate': 0
        }
        
        for source_name, source_data in processed_results.get('processed_sources', {}).items():
            if source_data.get('success'):
                metrics['successful_sources'] += 1
                
                if source_data.get('normalized_data'):
                    metrics['sources_with_data'] += 1
                
                validation_errors = len(source_data.get('validation_errors', []))
                metrics['total_validation_errors'] += validation_errors
                
                # Calcula completude dos dados por fonte
                normalized_data = source_data.get('normalized_data', {})
                metrics['data_completeness'][source_name] = len(normalized_data)
        
        # Calcula taxa de sucesso do processamento
        if metrics['total_sources'] > 0:
            metrics['processing_success_rate'] = (
                metrics['sources_with_data'] / metrics['total_sources']
            ) * 100
        
        return metrics


if __name__ == "__main__":
    # Teste do processador
    processor = DataProcessor()
    
    # Dados de exemplo para teste
    sample_results = {
        'timestamp': datetime.now().isoformat(),
        'execution_mode': 'parallel',
        'summary': {'total_sources': 2, 'successful': 1, 'failed': 1},
        'sources': {
            'ibge': {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': 2.5,
                'data': {
                    'municipio_info': {
                        'nome': 'Passo Fundo',
                        'id': 4314902,
                        'microrregiao': {
                            'nome': 'Passo Fundo',
                            'mesorregiao': {
                                'nome': 'Noroeste Rio-grandense',
                                'UF': {'nome': 'Rio Grande do Sul', 'sigla': 'RS'}
                            }
                        }
                    }
                }
            }
        }
    }
    
    processed = processor.process_collection_results(sample_results)
    print("Processamento concluído:")
    print(f"- Fontes processadas: {len(processed['processed_sources'])}")
    print(f"- Taxa de sucesso: {processed['quality_metrics']['processing_success_rate']:.1f}%")

