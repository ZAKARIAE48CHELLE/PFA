import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../config/api.config';
import { AuthService } from './auth.service';

export interface Negociation {
  id: string;
  rounds: number;
  prixInitial: number;
  prixFinal: number;
  acheteurId: string;
  produitId: string;
  offreId?: string;
}

export interface MessageNegociation {
  id?: string;
  negociationId: string;
  sender: 'ACHETEUR' | 'AGENT';
  content: string;
  price: number;
  timestamp?: string;
}

@Injectable({
  providedIn: 'root'
})
export class NegotiationService {
  private apiUrl = `${API_CONFIG.baseUrl}/negotiations`;

  constructor(private http: HttpClient, private authService: AuthService) { }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Authorization': `Bearer ${this.authService.getToken()}`,
      'ngrok-skip-browser-warning': 'true'
    });
  }

  getNegociations(): Observable<Negociation[]> {
    return this.http.get<Negociation[]>(this.apiUrl, { headers: this.getHeaders() });
  }

  getMessages(negoId: string): Observable<MessageNegociation[]> {
    return this.http.get<MessageNegociation[]>(`${this.apiUrl}/${negoId}/messages`, { headers: this.getHeaders() });
  }

  createNegociation(negociation: any): Observable<Negociation> {
    return this.http.post<Negociation>(this.apiUrl, negociation, { headers: this.getHeaders() });
  }

  saveMessage(message: MessageNegociation): Observable<MessageNegociation> {
    return this.http.post<MessageNegociation>(`${this.apiUrl}/messages`, message, { headers: this.getHeaders() });
  }

  ajusterNegociation(nego: Negociation, prixPropose: number, history: number[]): Observable<any> {
    const payload = {
      negociationId: nego.id,
      prixActuel: nego.prixFinal, // This should be the current seller price
      prixMin: (nego.prixInitial || nego.prixFinal) * 0.6, // Floor at 60% of original price
      prixPropose: prixPropose,
      roundActuel: (nego.rounds || 0) + 1, // We are asking for the NEXT round's response
      roundsMax: 5, // Hard cap at 5 rounds for quick negotiations
      historiqueOffres: history
    };
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/nego/ajuster`, payload, { headers: this.getHeaders() });
  }

  deleteNegociation(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`, { headers: this.getHeaders() });
  }
}
