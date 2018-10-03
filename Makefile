all: public
	./scripts/generate_pages.py
	hugo
	cd public && git add --all && git commit -m "Publishing to gh-pages" && cd ..

public:
	git woktree prune
	git worktree add -B gh-pages public origin/gh-pages

publish:
	cd public && git push origin gh-pages

clean:
	rm -rf public
