import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { EnvelopeIcon, PhoneIcon, MapPinIcon } from '@heroicons/react/24/outline'

export default function ContactPage() {
  return (
    <>
      <Helmet><title>Contact — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto text-center mb-12">
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Contact Us</h1>
            <p className="text-brand-300">Get in touch with the Kenya Youth Intercounty Sports Association</p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {[
              {
                icon: EnvelopeIcon,
                title: 'Email',
                detail: 'info@kyisa.co.ke',
                sub: 'We reply within 24 hours',
              },
              {
                icon: PhoneIcon,
                title: 'Phone',
                detail: '+254 700 000 000',
                sub: 'Mon-Fri, 8am — 5pm EAT',
              },
              {
                icon: MapPinIcon,
                title: 'Office',
                detail: 'Nairobi, Kenya',
                sub: 'Sports House, 2nd Floor',
              },
            ].map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="text-center p-6 rounded-xl bg-surface-elevated border border-border"
              >
                <item.icon className="h-8 w-8 text-accent mx-auto mb-3" />
                <h3 className="font-semibold text-brand-50 mb-1">{item.title}</h3>
                <p className="text-brand-100">{item.detail}</p>
                <p className="text-xs text-brand-400 mt-1">{item.sub}</p>
              </motion.div>
            ))}
          </div>

          {/* Quick form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-12 max-w-2xl mx-auto"
          >
            <div className="rounded-xl bg-surface-elevated border border-border p-6 sm:p-8">
              <h2 className="text-lg font-semibold text-brand-50 mb-6">Send a Message</h2>
              <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-brand-200 mb-1">Name</label>
                    <input
                      type="text"
                      className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-brand-200 mb-1">Email</label>
                    <input
                      type="email"
                      className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
                      placeholder="you@example.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-brand-200 mb-1">Subject</label>
                  <input
                    type="text"
                    className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
                    placeholder="How can we help?"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-brand-200 mb-1">Message</label>
                  <textarea
                    rows={5}
                    className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent resize-none"
                    placeholder="Your message..."
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-2.5 bg-accent text-brand-900 font-semibold rounded-lg hover:bg-accent-light transition-colors"
                >
                  Send Message
                </button>
              </form>
            </div>
          </motion.div>
        </div>
      </section>
    </>
  )
}
