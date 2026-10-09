// Read the actual QAM surface. Document visibility alone does not establish
// whether a persistent Steam sidebar is on screen.
export function quickAccessVisibility(documents: Document[], classNames: string[]): boolean | null {
	let foundMenu = false;
	for (const doc of documents) {
		// Prefer the sidebar itself over its full-screen transparent container.
		for (const name of classNames) {
			if (!name) continue;
			const menus = Array.from(doc.getElementsByClassName(name));
			if (!menus.length) continue;
			foundMenu = true;
			if (doc.hidden) break;
			const view = doc.defaultView;
			if (!view) break;
			for (const menu of menus) {
				if (!menu.isConnected) continue;
				const rect = menu.getBoundingClientRect();
				if (rect.width <= 0 || rect.height <= 0 || rect.right <= 0 || rect.bottom <= 0 || rect.left >= view.innerWidth || rect.top >= view.innerHeight) continue;
				let visible = true;
				for (let node: Element | null = menu; node; node = node.parentElement) {
					const style = view.getComputedStyle(node);
					if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse" || Number(style.opacity) === 0) {
						visible = false;
						break;
					}
				}
				if (visible) return true;
			}
			break;
		}
	}
	// Missing markup is unknown, rather than an assertion that QAM is open.
	return foundMenu ? false : null;
}
