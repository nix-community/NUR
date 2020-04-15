all: public
	./scripts/generate_pages.py
	hugo
	git -C public add --all
	git -C public commit -m "Publishing to gh-pages"

public:
	git worktree prune
	git worktree add -B gh-pages public origin/gh-pages

publish:
	git -C public push origin gh-pages

clean:
	rm -rf public
