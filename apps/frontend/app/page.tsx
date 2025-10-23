import Link from "next/link";
import { Github, ArrowRight } from "lucide-react";

const HomePage = () => {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-white bg-secondary">
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
        <section className="py-24 md:py-32">
          <div className="container mx-auto px-6">
            <div className="mx-auto max-w-4xl text-center">
              <h1 className="mb-6 text-5xl font-extrabold leading-tight md:text-6xl">
                From Slack message to PR{" "}
                <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                  in minutes
                </span>
              </h1>
              <p className="mx-auto mb-10 max-w-3xl text-lg text-muted-foreground md:text-xl">
                Slack bot that turns feature requests into production-ready pull
                requests. Multiple AI agents work in parallel, write tests, and
                deliver code ready for human review.
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

        {/* Real Example Section */}
        <section className="bg-gradient-to-br from-muted to-secondary py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">
              See It In Action
            </h2>
            <div className="mx-auto max-w-7xl">
              <div className="flex flex-col gap-12 lg:flex-row lg:items-start lg:justify-center">
                {/* Left side - Annotations */}
                <div className="flex flex-col gap-6 lg:mt-8 lg:max-w-sm">
                  {[
                    {
                      number: 1,
                      title: "Developer makes request",
                      description:
                        "Mention @dogwalker with feature request in any Slack channel or thread",
                      marginTop: "mt-8",
                    },
                    {
                      number: 2,
                      title: "Dog acknowledges task",
                      description:
                        "AI agent confirms it's working on the request",
                      marginTop: "mt-16",
                    },
                    {
                      number: 3,
                      title: "Creates draft PR with plan",
                      description:
                        "Generates implementation plan and opens draft PR for early review",
                      marginTop: "",
                    },
                    {
                      number: 4,
                      title: "Bi-directional feedback",
                      description:
                        "Developer can request changes at any time—AI incorporates feedback",
                      marginTop: "",
                    },
                    {
                      number: 5,
                      title: "PR ready for review",
                      description:
                        "Dog completes work, runs tests, and marks PR ready for human review",
                      marginTop: "",
                    },
                  ].map((step) => (
                    <div
                      key={step.number}
                      className={`relative flex items-start gap-4 rounded-xl border-2 border-primary/20 bg-background p-4 shadow-sm hover:border-primary/40 hover:shadow-md transition-all after:absolute after:right-0 after:top-1/2 after:h-0 after:w-0 after:translate-x-full after:-translate-y-1/2 after:border-8 after:border-transparent after:border-l-primary/30 after:content-[''] lg:after:block after:hidden ${step.marginTop}`}
                    >
                      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                        {step.number}
                      </div>
                      <div>
                        <h4 className="mb-1 font-semibold text-foreground">
                          {step.title}
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          {step.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Right side - Slack screenshot */}
                <div className="flex flex-shrink-0 flex-col items-center gap-6">
                  <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
                    <img
                      src="/slack-thread-example.png"
                      alt="Real Slack thread showing Dogwalker in action"
                      className="h-auto w-full lg:w-[450px]"
                    />
                  </div>
                  <Link
                    href="https://github.com/BryanOwens012/dog-park/pull/45"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg border-2 border-primary bg-background px-6 py-3 text-base font-semibold text-primary transition-all hover:-translate-y-0.5 hover:bg-primary hover:text-primary-foreground hover:shadow-lg"
                  >
                    <Github className="h-5 w-5" />
                    View the Pull Request
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">
              Key Features
            </h2>
            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  icon: "🤝",
                  title: "Bi-Directional Communication",
                  description:
                    "Reply in Slack threads to give feedback while dogs are working. AI responds to questions and incorporates your input in real-time.",
                },
                {
                  icon: "🐕",
                  title: "Multi-Agent Architecture",
                  description:
                    'Configure multiple AI "dogs" that work in parallel with load balancing. Scale from 1 to N agents as your team grows.',
                },
                {
                  icon: "📸",
                  title: "Visual Documentation",
                  description:
                    "Automatic before/after screenshots for UI changes. Include URLs in tasks to replicate designs from reference websites.",
                },
                {
                  icon: "🔍",
                  title: "Proactive Research",
                  description:
                    "Dogs autonomously search for current docs, API changes, and best practices. Always uses up-to-date information.",
                },
                {
                  icon: "✅",
                  title: "Quality Assurance",
                  description:
                    "Three-phase workflow: self-review for improvements, comprehensive test writing, and validation before marking PR ready.",
                },
                {
                  icon: "🔒",
                  title: "Self-Hosted",
                  description:
                    "Run on your infrastructure. Your code never leaves your control. MIT licensed and fully open source.",
                },
              ].map((feature, index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-border bg-card p-8 transition-all hover:-translate-y-1 hover:border-primary hover:shadow-lg"
                >
                  <div className="mb-4 text-5xl">{feature.icon}</div>
                  <h3 className="mb-3 text-xl font-semibold">
                    {feature.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="bg-secondary py-20">
          <div className="container mx-auto px-6">
            <h2 className="mb-12 text-center text-4xl font-bold">
              Built With Modern Tools
            </h2>
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
                  <div className="text-sm text-muted-foreground">
                    {tech.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="bg-gradient-to-r from-primary to-accent py-20 text-primary-foreground">
          <div className="container mx-auto px-6">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="mb-4 text-4xl font-bold">
                Ready to automate your code reviews?
              </h2>
              <p className="mb-8 text-lg opacity-95">
                Clone the repo, configure your dogs, and start shipping features
                faster.
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
              <p className="text-muted-foreground">
                Slack bot that turns feature requests into production-ready pull
                requests
              </p>
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
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
