import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../config/api.config';
import { AuthService } from './auth.service';

export interface Audit {
  id: string;
  type: string;
  severite: string;
  message: string;
  agentSource: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuditService {
  private apiUrl = `${API_CONFIG.baseUrl}/audits`;

  constructor(private http: HttpClient, private authService: AuthService) { }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Authorization': `Bearer ${this.authService.getToken()}`,
      'ngrok-skip-browser-warning': 'true'
    });
  }

  getAudits(): Observable<Audit[]> {
    return this.http.get<Audit[]>(this.apiUrl, { headers: this.getHeaders() });
  }
}
