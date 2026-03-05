import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'

export default function AboutPage() {
  return (
    <>
      <Helmet><title>About — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-6">About KYISA</h1>

            <div className="prose prose-invert max-w-none space-y-6 text-brand-200 leading-relaxed">
              <p>
                The <strong className="text-brand-50">Kenya Youth Intercounty Sports Association (KYISA)</strong> is the
                premier youth sports body in Kenya, bringing together counties to compete across nine sporting
                disciplines in an annual championship format.
              </p>

              <h2 className="text-xl font-semibold text-brand-50 mt-8 mb-3">Our Mission</h2>
              <p>
                To develop and promote competitive youth sports at the intercounty level, nurturing talent,
                building character, and fostering unity among Kenya's diverse communities through sport.
              </p>

              <h2 className="text-xl font-semibold text-brand-50 mt-8 mb-3">Our Sports</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  "Football (Men's & Women's)",
                  "Volleyball (Men's & Women's)",
                  "Basketball (Men's & Women's)",
                  "Handball (Men's & Women's)",
                  'Netball (Open)',
                ].map((sport) => (
                  <div key={sport} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-elevated border border-border">
                    <span className="h-2 w-2 rounded-full bg-accent" />
                    <span className="text-brand-100">{sport}</span>
                  </div>
                ))}
              </div>

              <h2 className="text-xl font-semibold text-brand-50 mt-8 mb-3">History</h2>
              <p>
                Now entering its 11th edition, KYISA has grown from a small regional initiative into a
                nationwide championship featuring 20+ counties, 200+ teams, and thousands of young athletes
                competing for glory and recognition.
              </p>

              <h2 className="text-xl font-semibold text-brand-50 mt-8 mb-3">Governance</h2>
              <p>
                KYISA operates under the auspices of Kenya's sports regulatory framework and works closely with
                County Governments, the Ministry of Sports, and the Football Kenya Federation (FKF) to ensure
                all competitions meet national and international standards.
              </p>
            </div>
          </motion.div>
        </div>
      </section>
    </>
  )
}
