import { useState, useEffect } from 'react'
import {
  Activity, Database, AlertTriangle, CheckCircle, Clock,
  TrendingUp, MapPin, Users, DollarSign, BarChart3,
  RefreshCw, Wifi, WifiOff, ChevronRight
} from 'lucide-react'

const API_BASE = 'http://localhost:5001'

function StatusBadge({ ok, label }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
      {ok ? <Wifi size={10}/> : <WifiOff size={10}/>}
      {label}
    </span>
  )
}

function Card({ children, className = '' }) {
  return <div className={`bg-white rounded-xl shadow-sm border border-gray-100 ${className}`}>{children}</div>
}

function MetricCard({ icon: Icon, color, label, value, sub }) {
  return (
    <Card className="p-5">
      <div className="flex items-start gap-4">
        <div className={`p-2.5 rounded-lg ${color}`}>
          <Icon size={22} className="text-white" />
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
      </div>
    </Card>
  )
}

export default function App() {
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const [apiStatus, setApiStatus] = useState({
    ibge: true, bcb: true, transparencia: false, dados_gov: true
  })
  const [collectResult, setCollectResult] = useState(null)

  const fetchStatus = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/data/apis/status`)
      if (r.ok) {
        const d = await r.json()
        setApiStatus(d)
      }
    } catch (_) {}
    setLastUpdate(new Date())
  }

  useEffect(() => {
    fetchStatus()
    const t = setInterval(fetchStatus, 30000)
    return () => clearInterval(t)
  }, [])

  const runCollection = async () => {
    setLoading(true)
    setCollectResult(null)
    try {
      const r = await fetch(`${API_BASE}/api/data/collect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_to_db: true })
      })
      const d = await r.json()
      setCollectResult({ ok: r.ok, msg: r.ok ? 'Coleta concluída com sucesso!' : (d.error || 'Erro na coleta') })
      fetchStatus()
    } catch (e) {
      setCollectResult({ ok: false, msg: 'Erro de conexão com o servidor' })
    } finally {
      setLoading(false)
    }
  }

  const apis = [
    { key: 'ibge', name: 'IBGE', desc: 'Dados demográficos e econômicos municipais', url: 'servicodados.ibge.gov.br' },
    { key: 'bcb', name: 'Banco Central', desc: 'Indicadores econômicos nacionais (IPCA, Selic, Câmbio)', url: 'dadosabertos.bcb.gov.br' },
    { key: 'transparencia', name: 'Portal da Transparência', desc: 'Convênios e contratos federais (requer chave)', url: 'api.portaldatransparencia.gov.br' },
    { key: 'dados_gov', name: 'Dados.gov.br', desc: 'Datasets governamentais abertos', url: 'dados.gov.br' },
  ]

  const onlineCount = Object.values(apiStatus).filter(Boolean).length

  const tabs = [
    { id: 'overview', label: 'Visão Geral', icon: Activity },
    { id: 'apis', label: 'Status das APIs', icon: Database },
    { id: 'collect', label: 'Coleta de Dados', icon: RefreshCw },
    { id: 'alerts', label: 'Alertas', icon: AlertTriangle },
  ]

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <BarChart3 size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">Dashboard Passo Fundo</h1>
              <p className="text-xs text-gray-500">Monitoramento Municipal em Tempo Real</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500">
              <MapPin size={14} />
              <span>Passo Fundo/RS</span>
              <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs">IBGE 4314902</span>
            </div>
            <button
              onClick={runCollection}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Coletando...' : 'Coletar Dados'}
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <nav className="flex gap-0">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex items-center gap-2 px-4 py-3.5 text-sm font-medium border-b-2 transition-colors ${
                  tab === id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Notification */}
        {collectResult && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${collectResult.ok ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
            {collectResult.ok ? <CheckCircle size={18}/> : <AlertTriangle size={18}/>}
            <span className="text-sm font-medium">{collectResult.msg}</span>
            <button onClick={() => setCollectResult(null)} className="ml-auto text-current opacity-60 hover:opacity-100">✕</button>
          </div>
        )}

        {/* Overview Tab */}
        {tab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard icon={CheckCircle} color="bg-green-500" label="Status do Serviço" value="Ativo" sub="Sistema operacional" />
              <MetricCard icon={Database} color="bg-blue-500" label="APIs Disponíveis" value={`${onlineCount}/4`} sub={`${onlineCount} funcionando agora`} />
              <MetricCard icon={TrendingUp} color="bg-purple-500" label="Dados Coletados" value="1.2k+" sub="Registros armazenados" />
              <MetricCard icon={AlertTriangle} color="bg-amber-500" label="Alertas Ativos" value="2" sub="1 aviso, 1 informativo" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <MapPin size={16} className="text-blue-600" /> Informações Municipais
                </h3>
                <div className="space-y-3">
                  {[
                    { icon: Users, label: 'População Estimada', value: '~200.000 hab.' },
                    { icon: MapPin, label: 'Região', value: 'Norte do RS' },
                    { icon: DollarSign, label: 'PIB per capita', value: 'R$ 45.000+' },
                    { icon: BarChart3, label: 'Código IBGE', value: '4314902' },
                  ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <div className="flex items-center gap-2 text-gray-600">
                        <Icon size={14} />
                        <span className="text-sm">{label}</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">{value}</span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp size={16} className="text-blue-600" /> Indicadores Econômicos Nacionais
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: 'IPCA (12m)', value: '4,5%', color: 'text-red-600' },
                    { label: 'Taxa Selic', value: '11,75%', color: 'text-blue-600' },
                    { label: 'Dólar (USD)', value: 'R$ 5,20', color: 'text-green-600' },
                    { label: 'IBC-Br', value: '+2,1%', color: 'text-purple-600' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-500 mb-1">{label}</p>
                      <p className={`text-xl font-bold ${color}`}>{value}</p>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-3 flex items-center gap-1">
                  <Clock size={10}/> Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
                </p>
              </Card>
            </div>
          </div>
        )}

        {/* APIs Tab */}
        {tab === 'apis' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-gray-900">Status das APIs Governamentais</h2>
              <StatusBadge ok={onlineCount >= 3} label={`${onlineCount}/4 online`} />
            </div>
            {apis.map(({ key, name, desc, url }) => (
              <Card key={key} className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${apiStatus[key] ? 'bg-green-500' : 'bg-red-400'}`} />
                    <div>
                      <p className="font-semibold text-gray-900">{name}</p>
                      <p className="text-sm text-gray-500">{desc}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{url}</p>
                    </div>
                  </div>
                  <StatusBadge ok={apiStatus[key]} label={apiStatus[key] ? 'Funcionando' : 'Indisponível'} />
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Collect Tab */}
        {tab === 'collect' && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Coleta Manual de Dados</h2>
              <p className="text-sm text-gray-500 mb-6">
                Execute uma coleta completa de todas as fontes de dados governamentais integradas ao sistema.
                O processo pode levar até 60 segundos dependendo da disponibilidade das APIs.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                {apis.map(({ key, name }) => (
                  <div key={key} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className={`w-2 h-2 rounded-full ${apiStatus[key] ? 'bg-green-500' : 'bg-red-400'}`} />
                    <span className="text-sm text-gray-700">{name}</span>
                    <ChevronRight size={14} className="text-gray-400 ml-auto" />
                  </div>
                ))}
              </div>
              <button
                onClick={runCollection}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white py-3 rounded-lg font-medium transition-colors"
              >
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                {loading ? 'Executando coleta...' : 'Iniciar Coleta Completa'}
              </button>
            </Card>
            <Card className="p-6">
              <h3 className="font-semibold text-gray-900 mb-3">Configurações de Coleta</h3>
              <div className="space-y-2 text-sm">
                {[
                  ['Intervalo automático', 'A cada 30 minutos'],
                  ['Timeout por API', '30 segundos'],
                  ['Tentativas em caso de erro', '3 retentativas'],
                  ['Logs mantidos', 'Últimos 1.000 registros'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between py-2 border-b border-gray-50 last:border-0">
                    <span className="text-gray-500">{k}</span>
                    <span className="font-medium text-gray-900">{v}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Alerts Tab */}
        {tab === 'alerts' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card className="p-5 text-center">
                <p className="text-3xl font-bold text-amber-500">1</p>
                <p className="text-sm text-gray-500 mt-1">Avisos</p>
              </Card>
              <Card className="p-5 text-center">
                <p className="text-3xl font-bold text-red-500">0</p>
                <p className="text-sm text-gray-500 mt-1">Erros Críticos</p>
              </Card>
              <Card className="p-5 text-center">
                <p className="text-3xl font-bold text-blue-500">1</p>
                <p className="text-sm text-gray-500 mt-1">Informativos</p>
              </Card>
            </div>
            <Card className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Alertas Recentes</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-100 rounded-lg">
                  <AlertTriangle size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Portal da Transparência indisponível</p>
                    <p className="text-xs text-amber-600 mt-0.5">API requer chave de acesso. Configure em transparencia_collector.py</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                  <Activity size={16} className="text-blue-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-blue-800">Sistema inicializado com sucesso</p>
                    <p className="text-xs text-blue-600 mt-0.5">3 de 4 APIs disponíveis. Coleta automática ativa.</p>
                  </div>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <h3 className="font-semibold text-gray-900 mb-3">Configuração de Alertas</h3>
              <div className="space-y-2 text-sm">
                {[
                  ['APIs offline por mais de', '15 minutos'],
                  ['Coletas falhando por mais de', '2 horas'],
                  ['Tempo máximo de execução', '5 minutos'],
                  ['Sem dados novos por mais de', '1 hora'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between py-2 border-b border-gray-50 last:border-0">
                    <span className="text-gray-500">{k}</span>
                    <span className="font-medium text-gray-900">{v}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between text-xs text-gray-400">
          <span>© 2025 Prefeitura Municipal de Passo Fundo/RS — Dashboard de Monitoramento</span>
          <span className="flex items-center gap-1">
            <Clock size={11}/> {lastUpdate.toLocaleString('pt-BR')}
          </span>
        </div>
      </footer>
    </div>
  )
}
