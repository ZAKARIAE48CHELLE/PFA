import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../config/api.config';
import { AuthService } from './auth.service';

export interface SystemError {
  id: string;
  service: string;
  errorType: string;
  message: string;
  stackTrace?: string;
  createdAt: string;
  resolved: boolean;
  negociationId?: string;
  userId?: string;
  produitId?: string;
  agentName?: string;
  severity: string;
  durationMs?: number;
  payload?: string;
  endpoint?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ErrorDashboardService {
  
  private readonly BASE = `${API_CONFIG.baseUrl}/audits/errors`;

  constructor(private http: HttpClient, private authService: AuthService) {}

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Authorization': `Bearer ${this.authService.getToken()}`,
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true'
    });
  }

  getUnresolvedErrors(): Observable<SystemError[]> {
    return this.http.get<SystemError[]>(`${this.BASE}/unresolved`, { headers: this.getHeaders() });
  }

  getAllErrors(): Observable<SystemError[]> {
    return this.http.get<SystemError[]>(`${this.BASE}/all`, { headers: this.getHeaders() });
  }

  getStats(): Observable<any> {
    return this.http.get<any>(`${this.BASE}/stats`, { headers: this.getHeaders() });
  }

  resolveError(id: string): Observable<SystemError> {
    return this.http.put<SystemError>(`${this.BASE}/${id}/resolve`, {}, { headers: this.getHeaders() });
  }

  reportFrontendError(dto: Partial<SystemError>): Observable<SystemError> {
    // Standard headers here might be without authorization if user is guest, but standard is safe
    const h = new HttpHeaders({ 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' });
    return this.http.post<SystemError>(this.BASE, dto, { headers: h });
  }
}
