import "./App.css";

import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Sankey,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type AnyRecord = Record<string, unknown>;

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postFile<T>(url: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(url, { method: "POST", body: formData });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function useApi<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getJson<T>(url)
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [url]);

  return { data, loading, error };
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <header className="hero">
        <div>
          <div className="eyebrow">Hydrolix · FastAPI + React</div>
          <h1>Balance de Masas Cu/H2SO4</h1>
          <p>
            Plataforma operativa para balance mensual LIX/SX/EW y análisis detallado por pad,
            franja y módulo de riego.
          </p>
        </div>
        <div className="hero-chip-grid">
          <div className="hero-chip">
            <span>Motor</span>
            <strong>Heap + Global Balance</strong>
          </div>
          <div className="hero-chip">
            <span>Frontend</span>
            <strong>React</strong>
          </div>
          <div className="hero-chip">
            <span>Backend</span>
            <strong>FastAPI</strong>
          </div>
        </div>
      </header>

      <nav className="topnav">
        {[
          ["/", "Resumen"],
          ["/heap", "Heap / Pad"],
          ["/franja", "Franja"],
          ["/upload", "Carga"],
          ["/reports", "Reportes"],
        ].map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            {label}
          </NavLink>
        ))}
      </nav>

      <main>{children}</main>
    </div>
  );
}

function LoadingBlock({ message }: { message: string }) {
  return <div className="state-card">Cargando {message}...</div>;
}

function ErrorBlock({ message }: { message: string }) {
  return <div className="state-card error">No se pudo cargar: {message}</div>;
}

function KpiGrid({ cards }: { cards: Array<{ label: string; value: string; tone?: string }> }) {
  return (
    <section className="kpi-grid">
      {cards.map((card) => (
        <article key={card.label} className={`kpi-card tone-${card.tone ?? "slate"}`}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
    </section>
  );
}

function TableCard({ title, rows }: { title: string; rows: AnyRecord[] }) {
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>{title}</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 12).map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column}>{String(row[column] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function OverviewPage() {
  const { data, loading, error } = useApi<{
    cards: Array<{ label: string; value: string; tone: string }>;
    trends: Record<string, Array<number | string>>;
    inventory: AnyRecord[];
    tables: Record<string, AnyRecord[]>;
  }>("/api/monthly/overview");

  if (loading) return <LoadingBlock message="resumen mensual" />;
  if (error || !data) return <ErrorBlock message={error ?? "sin datos"} />;

  const trendRows = (data.trends.periods as string[]).map((period, index) => ({
    periodo: period,
    cuAlimentadoT: Number(data.trends.cuAlimentadoT[index]),
    cuCatodosT: Number(data.trends.cuCatodosT[index]),
    recLix: Number(data.trends.recuperacionLixPct[index]),
    recSx: Number(data.trends.recuperacionSxPct[index]),
    recEw: Number(data.trends.recuperacionEwPct[index]),
    recGlobal: Number(data.trends.recuperacionGlobalPct[index]),
    acidNeto: Number(data.trends.acidNetoKgKg[index]),
    inventario: Number(data.trends.inventarioCuT[index]),
  }));

  return (
    <>
      <KpiGrid cards={data.cards} />

      <section className="chart-grid chart-grid-wide">
        <article className="panel">
          <div className="panel-header">
            <h3>Cu alimentado vs cátodos</h3>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={trendRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="cuAlimentadoT" fill="#b35c2e" name="Cu alimentado (t)" />
              <Bar dataKey="cuCatodosT" fill="#2d7f7a" name="Cu cátodos (t)" />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Recuperación por etapa</h3>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={trendRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="recLix" stroke="#213547" strokeWidth={2} name="LIX" />
              <Line type="monotone" dataKey="recSx" stroke="#b35c2e" strokeWidth={2} name="SX" />
              <Line type="monotone" dataKey="recEw" stroke="#d1a126" strokeWidth={2} name="EW" />
              <Line type="monotone" dataKey="recGlobal" stroke="#2d7f7a" strokeWidth={3} name="Global" />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Consumo neto de ácido</h3>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trendRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="acidNeto" stroke="#d1a126" fill="rgba(209,161,38,0.35)" name="kg/kg Cu" />
            </AreaChart>
          </ResponsiveContainer>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Inventario Cu en pilas</h3>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="inventario" stroke="#213547" strokeWidth={3} name="Inventario Cu (t)" />
            </LineChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="split-grid">
        <TableCard title="Balance global" rows={data.tables.global} />
        <TableCard title="Inventario de pilas" rows={data.inventory} />
      </section>
    </>
  );
}

function HeapPage() {
  const { data: meta, loading: metaLoading, error: metaError } = useApi<{ heap: { cycles: Array<{ id: string }> } }>("/api/meta");
  const defaultCycle = meta?.heap.cycles[0]?.id ?? "";
  const [cycleId, setCycleId] = useState("");

  useEffect(() => {
    if (!cycleId && defaultCycle) setCycleId(defaultCycle);
  }, [cycleId, defaultCycle]);

  const { data, loading, error } = useApi<{
    cycleSummary: AnyRecord[];
    lifecycle: AnyRecord[];
    sankey: { nodes: Array<{ id: string; label: string }>; links: Array<{ source: string; target: string; value: number }> };
    alerts: Array<{ level: string; title: string; message: string }>;
  }>(cycleId ? `/api/heap/pad/${cycleId}` : "/api/heap/pad/__none__");

  if (metaLoading) return <LoadingBlock message="ciclos del heap" />;
  if (metaError || !meta) return <ErrorBlock message={metaError ?? "sin metadatos"} />;

  return (
    <>
      <section className="panel controls">
        <div className="panel-header">
          <h3>Vista Pad</h3>
        </div>
        <label className="field">
          <span>Ciclo</span>
          <select value={cycleId} onChange={(event) => setCycleId(event.target.value)}>
            {meta.heap.cycles.map((cycle) => (
              <option key={cycle.id} value={cycle.id}>
                {cycle.id}
              </option>
            ))}
          </select>
        </label>
      </section>

      {loading && <LoadingBlock message="pad" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <>
          <section className="alert-grid">
            {data.alerts.map((alert) => (
              <article key={alert.title} className={`alert-card ${alert.level}`}>
                <strong>{alert.title}</strong>
                <p>{alert.message}</p>
              </article>
            ))}
          </section>

          <section className="chart-grid chart-grid-wide">
            <article className="panel">
              <div className="panel-header">
                <h3>Mapa del pad por franja</h3>
              </div>
              <div className="franja-map">
                {data.lifecycle.map((row, index) => (
                  <div key={index} className={`franja-block state-${String(row.estado)}`}>
                    <span>{String(row.id_franja)}</span>
                    <strong>{String(row.estado)}</strong>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Sankey de ruteo</h3>
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <Sankey
                  data={{
                    nodes: data.sankey.nodes,
                    links: data.sankey.links.map((link) => ({
                      source: data.sankey.nodes.findIndex((node) => node.id === link.source),
                      target: data.sankey.nodes.findIndex((node) => node.id === link.target),
                      value: link.value,
                    })),
                  }}
                  nodePadding={24}
                  nodeWidth={14}
                  margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                />
              </ResponsiveContainer>
            </article>
          </section>

          <TableCard title="Resumen por franja" rows={data.cycleSummary} />
        </>
      )}
    </>
  );
}

function FranjaPage() {
  const { data: meta, loading: metaLoading, error: metaError } = useApi<{ heap: { cycles: Array<{ id: string }> } }>("/api/meta");
  const [cycleId, setCycleId] = useState("");
  const [franjaId, setFranjaId] = useState("");
  const { data: cycleData } = useApi<{ cycleSummary: AnyRecord[] }>(cycleId ? `/api/heap/pad/${cycleId}` : "/api/heap/pad/__none__");

  useEffect(() => {
    if (!cycleId && meta?.heap.cycles[0]?.id) {
      setCycleId(meta.heap.cycles[0].id);
    }
  }, [cycleId, meta]);

  useEffect(() => {
    const firstFranja = cycleData?.cycleSummary[0]?.id_franja;
    if (firstFranja) setFranjaId(String(firstFranja));
  }, [cycleData]);

  const { data, loading, error } = useApi<{
    alerts: Array<{ level: string; title: string; message: string }>;
    copperSummary: AnyRecord;
    acidSummary: AnyRecord;
    rlSummary: AnyRecord;
    recoveryCurve: AnyRecord[];
    daily: { acid: AnyRecord[] };
    moduleMetrics: AnyRecord[];
  }>(franjaId ? `/api/heap/franja/${franjaId}` : "/api/heap/franja/__none__");

  if (metaLoading) return <LoadingBlock message="franjas" />;
  if (metaError || !meta) return <ErrorBlock message={metaError ?? "sin metadatos"} />;

  const recoveryCards = data
    ? [
        { label: "Recuperación reconciliada", value: `${Number(data.copperSummary.recovery_pct).toFixed(1)}%`, tone: "copper" },
        { label: "Recuperación directa", value: `${Number(data.copperSummary.recovery_direct_pct).toFixed(1)}%`, tone: "slate" },
        { label: "Cierre de ácido", value: `${Number(data.acidSummary.acid_cierre_pct).toFixed(1)}%`, tone: "water" },
        { label: "RL total", value: `${Number(data.rlSummary.rl_total_m3_t).toFixed(2)} m³/t`, tone: "acid" },
      ]
    : [];

  return (
    <>
      <section className="panel controls">
        <div className="panel-header">
          <h3>Detalle por franja</h3>
        </div>
        <div className="control-grid">
          <label className="field">
            <span>Ciclo</span>
            <select value={cycleId} onChange={(event) => setCycleId(event.target.value)}>
              {meta.heap.cycles.map((cycle) => (
                <option key={cycle.id} value={cycle.id}>
                  {cycle.id}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Franja</span>
            <select value={franjaId} onChange={(event) => setFranjaId(event.target.value)}>
              {(cycleData?.cycleSummary ?? []).map((row, index) => (
                <option key={index} value={String(row.id_franja)}>
                  {String(row.id_franja)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {loading && <LoadingBlock message="franja" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <>
          <KpiGrid cards={recoveryCards} />

          <section className="chart-grid chart-grid-wide">
            <article className="panel">
              <div className="panel-header">
                <h3>Curva recuperación vs RL</h3>
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={data.recoveryCurve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="rl_total_acum_m3_t" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line dataKey="recovery_direct_pct" stroke="#213547" name="Directa" />
                  <Line dataKey="recovery_reconciled_pct" stroke="#b35c2e" strokeWidth={3} name="Reconciliada" />
                </ComposedChart>
              </ResponsiveContainer>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Consumo de ácido acumulado</h3>
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={data.daily.acid.map((row) => ({
                  fecha: String(row.fecha),
                  acidConsumido: Number(row.acid_consumido_kg) / 1000,
                  acidAsignado: Number(row.acid_asignado_kg) / 1000,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="fecha" hide />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="acidConsumido" stroke="#d1a126" fill="rgba(209,161,38,0.3)" name="Ácido consumido (t/d)" />
                  <Line type="monotone" dataKey="acidAsignado" stroke="#2d7f7a" name="Ácido asignado (t/d)" />
                </AreaChart>
              </ResponsiveContainer>
            </article>
          </section>

          <section className="alert-grid">
            {data.alerts.map((alert) => (
              <article key={alert.title} className={`alert-card ${alert.level}`}>
                <strong>{alert.title}</strong>
                <p>{alert.message}</p>
              </article>
            ))}
          </section>

          <TableCard title="Métricas por módulo" rows={data.moduleMetrics} />
        </>
      )}
    </>
  );
}

function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ rows: number; valid: boolean; issues: AnyRecord[]; preview: AnyRecord[] } | null>(null);
  const [processing, setProcessing] = useState(false);

  return (
    <section className="panel upload-panel">
      <div className="panel-header">
        <h3>Carga de datos</h3>
        <a className="button secondary" href="/api/template">
          Descargar template
        </a>
      </div>
      <label className="upload-drop">
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <span>{file ? file.name : "Selecciona un Excel o CSV mensual"}</span>
      </label>
      <div className="button-row">
        <button
          className="button"
          disabled={!file}
          onClick={async () => {
            if (!file) return;
            setPreview(await postFile("/api/upload/preview", file));
          }}
        >
          Previsualizar
        </button>
        <button
          className="button accent"
          disabled={!file}
          onClick={async () => {
            if (!file) return;
            setProcessing(true);
            try {
              await postFile("/api/upload/process", file);
              alert("Carga procesada");
            } finally {
              setProcessing(false);
            }
          }}
        >
          {processing ? "Procesando..." : "Procesar"}
        </button>
      </div>

      {preview && (
        <>
          <KpiGrid
            cards={[
              { label: "Filas", value: String(preview.rows), tone: "slate" },
              { label: "Estado", value: preview.valid ? "Válido" : "Con errores", tone: preview.valid ? "water" : "copper" },
            ]}
          />
          <TableCard title="Preview carga" rows={preview.preview} />
          <TableCard title="Issues detectados" rows={preview.issues} />
        </>
      )}
    </section>
  );
}

function ReportsPage() {
  const { data } = useApi<{ tables: { raw: AnyRecord[] } }>("/api/monthly/overview");
  const periods = useMemo(
    () => Array.from(new Set((data?.tables.raw ?? []).map((row) => String(row.periodo)))),
    [data],
  );
  const [period, setPeriod] = useState("");

  useEffect(() => {
    if (!period && periods[0]) setPeriod(periods[0]);
  }, [period, periods]);

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Reportes</h3>
      </div>
      <label className="field">
        <span>Período</span>
        <select value={period} onChange={(event) => setPeriod(event.target.value)}>
          {periods.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </label>
      <div className="button-row">
        <a className="button" href={`/api/reports/excel?period=${period}`}>
          Descargar Excel
        </a>
        <a className="button accent" href={`/api/reports/pdf?period=${period}`}>
          Descargar PDF
        </a>
      </div>
      <p className="note">
        Los reportes se generan desde FastAPI con las hojas `data_mensual`, `lix`, `sx`,
        `ew` y `balance_global`.
      </p>
    </section>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/heap" element={<HeapPage />} />
          <Route path="/franja" element={<FranjaPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
