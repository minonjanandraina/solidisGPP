# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ETL_Solidis_monthly import check_system, main

app = FastAPI(title="Solidis ETL API")


@app.on_event("startup")
def startup():
    check_system()


class RunPayload(BaseModel):
    start_str_date: str
    end_str_date: str
    retry: bool = True


@app.post("/run")
def run_etl(payload: RunPayload):
    try:
        main(payload.start_str_date, payload.end_str_date, retry=payload.retry)
        return {
            "status": "ok",
            "date_from": payload.start_str_date,
            "date_to": payload.end_str_date,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
