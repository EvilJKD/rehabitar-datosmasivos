import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Municipio, Convocatoria, DemografiaPunto, KPISummary } from '../models/municipio.model';

@Injectable({
  providedIn: 'root'
})
export class MunicipioService {
  private apiUrl = '/api';

  constructor(private http: HttpClient) {}

  // Obtener todos los municipios
  getMunicipios(filters?: {
    semaforo?: string;
    w_demo?: number;
    w_health?: number;
    w_grants?: number;
    w_infra?: number;
  }): Observable<Municipio[]> {
    let params = new HttpParams();
    if (filters) {
      if (filters.semaforo) params = params.set('semaforo', filters.semaforo);
      if (filters.w_demo) params = params.set('w_demo', filters.w_demo.toString());
      if (filters.w_health) params = params.set('w_health', filters.w_health.toString());
      if (filters.w_grants) params = params.set('w_grants', filters.w_grants.toString());
      if (filters.w_infra) params = params.set('w_infra', filters.w_infra.toString());
    }
    return this.http.get<Municipio[]>(`${this.apiUrl}/municipios`, { params });
  }

  // Obtener un municipio específico
  getMunicipioDetail(codigoIne: string, forceRefresh = false): Observable<Municipio> {
    let params = new HttpParams();
    if (forceRefresh) params = params.set('force_refresh', 'true');
    return this.http.get<Municipio>(`${this.apiUrl}/municipios/${codigoIne}`, { params });
  }

  // Forzar ingesta de un municipio
  triggerMunicipioIngestion(codigoIne: string): Observable<Municipio> {
    return this.http.post<Municipio>(`${this.apiUrl}/municipios/${codigoIne}/ingest`, {});
  }

  // Obtener demografía de un municipio
  getDemografia(codigoIne: string): Observable<{ serie_anual: DemografiaPunto[] }> {
    return this.http.get<{ serie_anual: DemografiaPunto[] }>(
      `${this.apiUrl}/municipios/${codigoIne}/demografia`
    );
  }

  // Obtener convocatorias
  getConvocatorias(filters?: {
    codigo_ine?: string;
    categoria?: string;
  }): Observable<Convocatoria[]> {
    let params = new HttpParams();
    if (filters) {
      if (filters.codigo_ine) params = params.set('codigo_ine', filters.codigo_ine);
      if (filters.categoria) params = params.set('categoria', filters.categoria);
    }
    return this.http.get<Convocatoria[]>(`${this.apiUrl}/convocatorias`, { params });
  }

  // Obtener centros sanitarios
  getCentrosSanitarios(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/centros-sanitarios`);
  }

  // Health check
  healthCheck(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}
