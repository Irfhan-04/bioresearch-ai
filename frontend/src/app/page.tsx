import Link from 'next/link'
import { ArrowRight, Database, Zap, BarChart3, Microscope } from 'lucide-react'

const features = [
  {
    icon: Database,
    title: 'Multi-Source Intelligence',
    desc: 'Unify PubMed, NIH funding, conference, and web signals into one research profile.',
  },
  {
    icon: Zap,
    title: 'Relevance Scoring',
    desc: 'Rank researchers by domain fit with explainable AI confidence signals.',
  },
  {
    icon: BarChart3,
    title: 'Explainable Insights',
    desc: 'Inspect ranking factors and summarize why each researcher matters.',
  },
]

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-white">
      <main className="mx-auto w-full max-w-6xl px-6 py-20">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 px-4 py-1 text-xs uppercase tracking-widest text-emerald-300">
          <Microscope className="h-4 w-4" /> AI-Powered Research Intelligence
        </div>
        <h1 className="max-w-4xl text-5xl font-bold leading-tight">Discover and rank biotech researchers with explainable AI.</h1>
        <p className="mt-6 max-w-2xl text-slate-300">
          BioResearch AI discovers, ranks, and explains biotech researchers from PubMed using
          four real ML components — semantic search, XGBoost scoring, SHAP explainability,and Claude-powered research intelligence.</p>
        <div className="mt-4 flex items-center gap-6 text-sm text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400"></span>
            3 searches/day without signing up
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-300"></span>
            20 searches/day with a free account
          </span>
        </div>
        <div className="mt-8 flex gap-4">
          <Link href="/dashboard/search" className="rounded-lg bg-emerald-400 px-5 py-3 font-semibold text-slate-950 inline-flex items-center gap-2">
            Try it now — no sign up <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/register" className="rounded-lg border border-slate-700 px-5 py-3 text-slate-300">
            Create free account
          </Link>
        </div>

        <section className="mt-16 grid gap-4 md:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <f.icon className="mb-3 h-5 w-5 text-emerald-300" />
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm text-slate-300">{f.desc}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  )
}
