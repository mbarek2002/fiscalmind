/** @type {import('next').NextConfig} */
const nextConfig = {
	reactStrictMode: true,
	webpack: (config, { dev }) => {
		// Projet lance depuis WSL sur un disque Windows (/mnt/c/...) : les
		// modifications faites cote Windows ne declenchent pas d'evenement inotify,
		// donc pas de rechargement. On passe en scrutation (polling) dans ce cas.
		if (dev && process.cwd().startsWith("/mnt/")) {
			config.watchOptions = { ...config.watchOptions, poll: 1000, aggregateTimeout: 300 };
		}
		return config;
	},
};

module.exports = nextConfig;
