"""Exclusive line-level output files; original source bytes are never rewritten."""
from io import BytesIO
from typing import Literal
from uuid import UUID
from zipfile import ZipFile, ZIP_DEFLATED
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from mcias.api import dependencies as deps
from mcias.api.features_routes import no_store
from mcias.services import result_service as service
from mcias.reporting_g7 import ReportBlocked
from mcias.report_exports_g7 import render_result_partition

router=APIRouter(prefix='/api/v1/result-files',tags=['Four preliminary outputs'],dependencies=[Depends(no_store)])

def perform(db,action):
    try:return action()
    except LookupError:db.rollback();raise HTTPException(404,'Result set or batch not found') from None
    except (ValueError,ReportBlocked) as exc:db.rollback();raise HTTPException(409,str(exc)) from None
    except RuntimeError:db.rollback();raise HTTPException(503,'Encrypted results storage unavailable') from None

@router.get('')
def listing(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),
            actor=Depends(deps.require_permission('reports.read')),db=Depends(deps.get_db)):
    return service.list_results(db,actor,offset,limit)

@router.post('/batches/{batch_id}',status_code=201)
def freeze(batch_id:UUID,actor=Depends(deps.require_permission('reports.create','claims.read')),db=Depends(deps.get_db)):
    def action():
        result=service.freeze(db,actor,str(batch_id));db.commit();return result
    return perform(db,action)

@router.get('/{result_id}/lines')
def lines(result_id:UUID,bucket:Literal['accepted','rejected','held','review']|None=None,
          offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),
          actor=Depends(deps.require_permission('reports.read','claims.read')),db=Depends(deps.get_db)):
    dataset=perform(db,lambda:service.read(db,actor,str(result_id)))
    rows=[{k:v for k,v in row.items() if k!='source_values'} for row in dataset['rows'] if bucket is None or row['bucket']==bucket]
    return {'items':rows[offset:offset+limit],'has_more':len(rows)>offset+limit,'summary':dataset['summary'],'stage':'preliminary'}

@router.get('/{result_id}/download')
def download(result_id:UUID,actor=Depends(deps.require_permission('reports.export','reports.read','claims.read')),db=Depends(deps.get_db)):
    dataset=perform(db,lambda:service.read(db,actor,str(result_id)))
    output=BytesIO()
    with ZipFile(output,'w',compression=ZIP_DEFLATED) as archive:
        for bucket in service.BUCKETS:
            archive.writestr(f'{bucket}.xlsx',render_result_partition(dataset,bucket))
    return Response(output.getvalue(),media_type='application/zip',headers={
        'Content-Disposition':f'attachment; filename="mcias-four-results-{result_id}.zip"','Cache-Control':'no-store'})
