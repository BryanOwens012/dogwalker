import Link from "next/link";
import { Github, ArrowRight } from "lucide-react";

const HomePage = () => {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
        <div className="container mx-auto px-6">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2 text-2xl font-bold">
              <span className="text-4xl">🐕</span>
              <span>Dogwalker</span>
            </div>
            <Link
              href="https://github.com/BryanOwens012/dogwalker"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <Github className="h-5 w-5" />
              View on GitHub
            </Link>
          </div>
        </div>
      </nav>

      <main>
        {/* Hero Section */}
        <section className="bg-gradient-to-br from-secondary to-muted py-24 md:py-32">
          <div className="container mx-auto px-6">
            <div className="mx-auto max-w-4xl text-center">
              <h1 className="mb-6 text-5xl font-extrabold leading-tight md:text-6xl">
                From Slack message to PR{" "}
                <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                  in minutes
                </span>
              </h1>
              <p className="mx-auto mb-10 max-w-3xl text-lg text-muted-foreground md:text-xl">
                Open-source, self-hosted AI coding system that turns feature requests into production-ready pull requests.
                Multiple AI agents work in parallel, write tests, and deliver code ready for human review.
              </p>
              <div className="flex justify-center">
                <Link
                  href="https://github.com/BryanOwens012/dogwalker"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-7 py-3.5 text-base font-semibold text-primary-foreground transition-all hover:-translate-y-0.5 hover:shadow-lg"
                >
                  Get Started
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">How It Works</h2>
            <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-4">
              {[
                {
                  number: 1,
                  title: "Mention in Slack",
                  description: (
                    <>
                      Type <code className="rounded bg-muted px-1.5 py-0.5 text-sm text-primary font-mono">@dogwalker add rate limiting to /api/login</code> in any channel or thread
                    </>
                  ),
                },
                {
                  number: 2,
                  title: "AI Creates Plan",
                  description: "AI dog generates implementation plan and creates draft PR for early review",
                },
                {
                  number: 3,
                  title: "Code + Test + Review",
                  description: "AI writes code, runs self-review, adds comprehensive tests, and validates everything works",
                },
                {
                  number: 4,
                  title: "PR Ready",
                  description: "Production-ready pull request marked for human review with complete documentation",
                },
              ].map((step) => (
                <div key={step.number} className="flex flex-col items-center text-center">
                  <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-2xl font-bold text-white">
                    {step.number}
                  </div>
                  <h3 className="mb-3 text-xl font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="bg-secondary py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">Key Features</h2>
            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  icon: "🤝",
                  title: "Bi-Directional Communication",
                  description: "Reply in Slack threads to give feedback while dogs are working. AI responds to questions and incorporates your input in real-time.",
                },
                {
                  icon: "🐕",
                  title: "Multi-Agent Architecture",
                  description: "Configure multiple AI \"dogs\" that work in parallel with load balancing. Scale from 1 to N agents as your team grows.",
                },
                {
                  icon: "📸",
                  title: "Visual Documentation",
                  description: "Automatic before/after screenshots for UI changes. Include URLs in tasks to replicate designs from reference websites.",
                },
                {
                  icon: "🔍",
                  title: "Proactive Research",
                  description: "Dogs autonomously search for current docs, API changes, and best practices. Always uses up-to-date information.",
                },
                {
                  icon: "✅",
                  title: "Quality Assurance",
                  description: "Three-phase workflow: self-review for improvements, comprehensive test writing, and validation before marking PR ready.",
                },
                {
                  icon: "🔒",
                  title: "Self-Hosted",
                  description: "Run on your infrastructure. Your code never leaves your control. MIT licensed and fully open source.",
                },
              ].map((feature, index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-border bg-card p-8 transition-all hover:-translate-y-1 hover:border-primary hover:shadow-lg"
                >
                  <div className="mb-4 text-5xl">{feature.icon}</div>
                  <h3 className="mb-3 text-xl font-semibold">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">Built With Modern Tools</h2>
            <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-3">
              {[
                { name: "Claude Sonnet 4.5", desc: "Code generation" },
                { name: "Aider", desc: "Smart code editing" },
                { name: "Celery + Redis", desc: "Task queue" },
                { name: "Slack Bolt", desc: "Communication" },
                { name: "Playwright", desc: "Web automation" },
                { name: "Python", desc: "Backend" },
              ].map((tech, index) => (
                <div
                  key={index}
                  className="rounded-xl border border-border bg-secondary p-6 text-center transition-all hover:-translate-y-0.5 hover:border-primary"
                >
                  <div className="font-semibold">{tech.name}</div>
                  <div className="text-sm text-muted-foreground">{tech.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="bg-gradient-to-r from-primary to-accent py-20 text-primary-foreground">
          <div className="container mx-auto px-6">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="mb-4 text-4xl font-bold">Ready to automate your code reviews?</h2>
              <p className="mb-8 text-lg opacity-95">
                Clone the repo, configure your dogs, and start shipping features faster.
              </p>
              <Link
                href="https://github.com/BryanOwens012/dogwalker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-white px-7 py-3.5 text-base font-semibold text-primary transition-all hover:bg-secondary"
              >
                <Github className="h-5 w-5" />
                Get Started on GitHub
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-secondary py-12">
        <div className="container mx-auto px-6">
          <div className="mb-8 flex flex-col justify-between gap-8 md:flex-row">
            <div>
              <div className="mb-2 flex items-center gap-2 text-2xl font-bold">
                <span className="text-4xl">🐕</span>
                <span>Dogwalker</span>
              </div>
              <p className="text-muted-foreground">Open-source, self-hosted AI coding system</p>
            </div>
            <div className="flex flex-col gap-4 md:flex-row md:gap-8">
              <Link
                href="https://github.com/BryanOwens012/dogwalker"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                GitHub
              </Link>
              <Link
                href="https://github.com/BryanOwens012/dogwalker/blob/main/docs/DEPLOYMENT.md"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                Deployment Guide
              </Link>
              <Link
                href="https://github.com/BryanOwens012/dogwalker/blob/main/docs/ARCHITECTURE.md"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                Architecture
              </Link>
              <Link
                href="https://github.com/BryanOwens012/dogwalker/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                Issues
              </Link>
            </div>
          </div>
          <div className="border-t border-border pt-8 text-center">
            <p className="text-sm text-muted-foreground">
              MIT License &copy; 2025 Dogwalker Contributors
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
