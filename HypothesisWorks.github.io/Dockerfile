FROM ruby:2.4-alpine3.6

LABEL maintainer "Alex Chan <alex@alexwlchan.net>"
LABEL description "Local build image for HypothesisWorks.github.io"

COPY Gemfile .
COPY Gemfile.lock .

RUN apk update && \
    apk add build-base git make nodejs
RUN bundle install

WORKDIR /site

ENTRYPOINT ["bundle", "exec", "jekyll"]
