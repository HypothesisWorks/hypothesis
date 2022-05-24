BUILD_IMAGE = hypothesisworks/hypothesisworks.github.io
SERVE_CONTAINER = server

ROOT = $(shell git rev-parse --show-toplevel)


.docker/build: Dockerfile Gemfile Gemfile.lock
	docker build --tag $(BUILD_IMAGE) .
	mkdir -p .docker
	touch .docker/build


build: .docker/build
	docker run --volume $(SRC):/site $(BUILD_IMAGE) build

serve: .docker/build
	@# Clean up old running containers
	@docker stop $(SERVE_CONTAINER) >/dev/null 2>&1 || true
	@docker rm $(SERVE_CONTAINER) >/dev/null 2>&1 || true

	docker run \
		--publish 5858:5858 \
		--volume $(ROOT):/site \
		--name $(SERVE_CONTAINER) \
		--hostname $(SERVE_CONTAINER) \
		--tty $(BUILD_IMAGE) \
		serve --host $(SERVE_CONTAINER) --port 5858 --watch

Gemfile.lock: Gemfile
	docker run \
		--volume $(ROOT):/site \
		--workdir /site \
		--tty $(shell cat Dockerfile | grep FROM | awk '{print $$2}') \
		bundle lock --update


.PHONY: build serve
