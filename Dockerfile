FROM python:3.8 as main

ARG WORKDIR=/exec

WORKDIR ${WORKDIR}

ENV FREECAD_LIB_DIR=/usr/lib/FreeCAD

ENV PYTHONPATH="${PYTHONPATH}:${FREECAD_LIB_DIR}"

COPY squashfs-root/usr/lib/ ${FREECAD_LIB_DIR}/

COPY ifcopenshell/ ${WORKDIR}/ifcopenshell/

COPY honeybee_ifc ${WORKDIR}/honeybee_ifc/

COPY requirements.txt ${WORKDIR}

RUN pip install -r requirements.txt

FROM main as dev

ARG WORKDIR=/exec

COPY dev-requirements.txt ${WORKDIR}

RUN pip install -r dev-requirements.txt