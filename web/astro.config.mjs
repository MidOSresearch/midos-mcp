// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
	site: 'https://midos.dev',
	base: '/',
	integrations: [
		sitemap(),
		starlight({
			title: 'MidOS',
			description: 'Curated Knowledge for AI Agents — 57 MCP tools, 1284 knowledge chunks, 104 skills, 22900 vectors.',
			logo: {
				light: './src/assets/logo-light.svg',
				dark: './src/assets/logo-dark.svg',
				replacesTitle: false,
			},
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/MidOSresearch/midos-mcp' },
			],
			editLink: {
				baseUrl: 'https://github.com/MidOSresearch/midos-web/edit/main/web/',
			},
			head: [
				// Analytics — Umami (privacy-first, cookie-free)
				{
					tag: 'script',
					attrs: {
						defer: true,
						src: 'https://cloud.umami.is/script.js',
						'data-website-id': '66971f34-c5c7-4949-bedd-36a02f66e55e',
						'data-domains': 'midos.dev',
					},
				},
				// OpenGraph
				{ tag: 'meta', attrs: { property: 'og:type', content: 'website' } },
				{ tag: 'meta', attrs: { property: 'og:site_name', content: 'MidOS' } },
				{ tag: 'meta', attrs: { property: 'og:image', content: '/og-image.png' } },
				{ tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
				{ tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
				// Twitter Card
				{ tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
				{ tag: 'meta', attrs: { name: 'twitter:image', content: '/og-image.png' } },
				// JSON-LD Structured Data
				{
					tag: 'script',
					attrs: { type: 'application/ld+json' },
					content: JSON.stringify({
						'@context': 'https://schema.org',
						'@type': 'SoftwareApplication',
						name: 'MidOS',
						applicationCategory: 'DeveloperApplication',
						operatingSystem: 'Cross-platform',
						description: 'MCP Community Library — Curated knowledge, skills, and tools for AI agents. 57 MCP tools, 1284 knowledge chunks, 104 skills.',
						url: 'https://midos.dev',
						author: {
							'@type': 'Organization',
							name: 'MidOS Research',
							url: 'https://github.com/MidOSresearch',
						},
						offers: {
							'@type': 'Offer',
							price: '0',
							priceCurrency: 'USD',
							description: 'Free community tier with 100 queries/month',
						},
						softwareRequirements: 'Python 3.10+, MCP-compatible client (Claude Desktop, Cursor, VS Code)',
					}),
				},
			],
			customCss: ['./src/styles/custom.css'],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Quick Start', slug: 'quickstart' },
						{ label: 'Architecture', slug: 'architecture' },
						{ label: 'Access Tiers', slug: 'tiers' },
					],
				},
				{
					label: 'Tool Catalog',
					items: [
						{ label: 'Overview', slug: 'tools/overview' },
						{ label: 'Free Tools (9)', slug: 'tools/free' },
						{ label: 'Dev Tools (6)', slug: 'tools/dev' },
						{ label: 'Pro Tools (5)', slug: 'tools/pro' },
						{ label: 'Admin Tools (16)', slug: 'tools/admin' },
						{ label: 'Marketplace (5)', slug: 'tools/marketplace' },
						{ label: 'QA & Community (6)', slug: 'tools/qa' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Try MidOS', slug: 'guides/try-it' },
						{ label: 'Agent Onboarding', slug: 'guides/agent-onboarding' },
						{ label: 'Semantic Search', slug: 'guides/semantic-search' },
						{ label: 'Session Management', slug: 'guides/sessions' },
					],
				},
			],
		}),
	],
});
