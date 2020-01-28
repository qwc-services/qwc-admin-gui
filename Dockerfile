# WSGI service environment

FROM husseinkabbout/qwc-docker

# Install service packages if needed
RUN apk add --no-cache --update postgresql-dev gcc python3-dev musl-dev git

# maybe set locale here if needed

ADD . /srv/qwc_service
RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt
