import Link from 'next/link'
import { ArrowRight, Database, Zap, BarChart3, Shield, Microscope } from 'lucide-react'

const features = [
  {
    icon: Database,
    title: 'Multi-Source Intelligence',
    desc: 'PubMed, NIH funding, LinkedIn, and conference records — unified into one precision dataset.',
    accent: '#00d68f',
  },
  {
    icon: Zap,
    title: 'AI Propensity Scoring',
    desc: 'Rank every prospect by adoption likelihood. No guesswork — pure data signal.',
    accent: '#a78bfa',
  },
  {
    icon: BarChart3,
    title: 'Pipeline Intelligence',
    desc: 'Track from discovery to close. Export to CRM or download as CSV, Excel, or JSON.',
    accent: '#38bdf8',
  },
  {
    icon: Shield,
    title: 'Team Collaboration',
    desc: 'Shared pipelines, role-based access, real-time alerts — built for BD teams.',
    accent: '#fbbf24',
  },
]

const stats = [
  { value: '10K+', label: 'Researchers indexed' },
  { value: '94%',  label: 'Scoring accuracy'   },
  { value: '5×',   label: 'Faster prospecting' },
  { value: '3',    label: 'Data sources fused'  },
]

export default function Home() {
  return (
    <div
      className="flex min-h-screen flex-col"
      style={{
        background: 'hsl(222,47%,4%)',
        backgroundImage:
          'linear-gradient(rgba(255,255,255,0.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.022) 1px,transparent 1px)',
        backgroundSize: '44px 44px',
      }}
    >
      {/* Nav */}
      <header
        className="fixed inset-x-0 top-0 z-50 h-16 flex items-center border-b border-[rgba(255,255,255,0.055)]"
        style={{ background: 'rgba(10,16,32,0.82)', backdropFilter: 'blur(16px)' }}
      >
        <div className="container mx-auto flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(0,214,143,0.3)] bg-[rgba(0,214,143,0.1)]">
              <Microscope className="h-4 w-4 text-[#00d68f]" />
            </div>
            <div>
              <span className="font-syne font-700 text-white text-sm tracking-tight">BioLead</span>
              <span className="ml-2 font-mono-dm text-[10px] text-zinc-600 uppercase tracking-widest">Intelligence</span>
            </div>
          </div>
          <nav className="flex items-center gap-3">
            <Link href="/login" className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors rounded-md hover:bg-white/[0.05]">
              Sign in
            </Link>
            <Link
              href="/register"
              className="flex items-center gap-2 px-4 py-2 text-sm font-600 font-syne rounded-lg transition-all"
              style={{ background: '#00d68f', color: 'hsl(222,47%,4%)', boxShadow: '0 0 20px rgba(0,214,143,0.35)' }}
            >
              Get started <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 pt-16">
        {/* Hero */}
        <section className="relative overflow-hidden py-36 md:py-52">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{ background: 'radial-gradient(ellipse 65% 55% at 50% 45%, rgba(0,214,143,0.08), transparent 70%)' }}
          />
          <div className="container mx-auto px-6 text-center relative z-10">
            <div
              className="inline-flex items-center gap-2 rounded-full border border-[rgba(0,214,143,0.25)] bg-[rgba(0,214,143,0.07)] px-4 py-1.5 mb-8 animate-fade-up"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[#00d68f] animate-pulse" />
              <span className="font-mono-dm text-xs text-[#00d68f] tracking-widest uppercase">AI-Powered Lead Intelligence</span>
            </div>

            <h1
              className="font-syne text-5xl font-800 tracking-tight sm:text-6xl md:text-7xl mx-auto max-w-4xl animate-fade-up delay-100"
              style={{ lineHeight: 1.05 }}
            >
              Find Every Biotech{' '}
              <span style={{
                background: 'linear-gradient(135deg,#00d68f 0%,#00c2ff 50%,#a78bfa 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>
                Prospect
              </span>{' '}
              Worth Pursuing
            </h1>

            <p className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed animate-fade-up delay-200">
              Precision-scored leads for 3D in-vitro model adoption — built for pharma &amp; biotech BD teams.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up delay-300">
              <Link
                href="/register"
                className="flex items-center gap-2 rounded-xl px-8 py-3.5 text-sm font-600 font-syne transition-all"
                style={{ background: '#00d68f', color: 'hsl(222,47%,4%)', boxShadow: '0 0 32px rgba(0,214,143,0.4)' }}
              >
                Start for free <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/dashboard"
                className="rounded-xl border border-[rgba(255,255,255,0.1)] px-8 py-3.5 text-sm font-medium text-zinc-300 hover:bg-white/[0.04] transition-colors"
              >
                View demo
              </Link>
            </div>
          </div>
        </section>

        {/* Stats strip */}
        <div
          className="border-y border-[rgba(255,255,255,0.055)]"
          style={{ background: 'rgba(11,18,36,0.65)', backdropFilter: 'blur(12px)' }}
        >
          <div className="container mx-auto px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s, i) => (
              <div key={i} className="text-center animate-fade-up" style={{ animationDelay: `${i * 80}ms` }}>
                <p className="font-mono-dm text-3xl font-500 text-[#00d68f]">{s.value}</p>
                <p className="text-[11px] text-zinc-500 mt-1 uppercase tracking-widest">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <section className="py-28">
          <div className="container mx-auto px-6">
            <div className="text-center mb-16">
              <p className="font-mono-dm text-xs uppercase tracking-widest text-zinc-600 mb-3">Platform capabilities</p>
              <h2 className="font-syne text-3xl font-700 text-white tracking-tight">Everything your BD team needs</h2>
            </div>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {features.map((f, i) => (
                <div
                  key={i}
                  className="rounded-xl border p-6 transition-transform duration-300 hover:-translate-y-1 animate-fade-up"
                  style={{
                    animationDelay: `${i * 80}ms`,
                    borderColor: `${f.accent}22`,
                    background: `radial-gradient(ellipse at top, ${f.accent}09, transparent 60%), rgba(11,18,36,0.88)`,
                    backdropFilter: 'blur(20px)',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
                  }}
                >
                  <div
                    className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg"
                    style={{ background: `${f.accent}15`, border: `1px solid ${f.accent}30` }}
                  >
                    <f.icon className="h-4 w-4" style={{ color: f.accent }} />
                  </div>
                  <h3 className="font-syne font-600 text-white text-sm mb-2">{f.title}</h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-24 relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{ background: 'radial-gradient(ellipse 55% 65% at 50% 50%, rgba(0,214,143,0.06), transparent 70%)' }}
          />
          <div className="container mx-auto px-6 text-center relative">
            <h2 className="font-syne text-4xl font-700 text-white tracking-tight mb-4">
              Start finding high-value leads today
            </h2>
            <p className="text-zinc-400 mb-8 max-w-sm mx-auto text-sm">Free forever up to 100 leads. No credit card.</p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-xl px-8 py-3.5 text-sm font-600 font-syne transition-all"
              style={{ background: '#00d68f', color: 'hsl(222,47%,4%)', boxShadow: '0 0 32px rgba(0,214,143,0.38)' }}
            >
              Create free account <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-[rgba(255,255,255,0.055)] py-8">
        <div className="container mx-auto px-6 flex items-center justify-between text-xs text-zinc-600">
          <div className="flex items-center gap-2">
            <Microscope className="h-3.5 w-3.5 text-[#00d68f]" />
            <span className="font-mono-dm">BioLead Intelligence</span>
          </div>
          <span>© 2026 · All rights reserved</span>
        </div>
      </footer>
    </div>
  )
}