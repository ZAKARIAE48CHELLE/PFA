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
  vendeurId?: string;
  produitId: string;
  offreId?: string;
  status?: string;
}

export interface MessageNegociation {
  id?: string;
  negociationId: string;
  sender: 'ACHETEUR' | 'VENDEUR' | 'AGENT_ACHETEUR' | 'AGENT_VENDEUR' | 'SYSTEM';
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

  getSellerNegociations(vendeurId: string): Observable<Negociation[]> {
    return this.http.get<Negociation[]>(`${this.apiUrl}/seller/${vendeurId}`, { headers: this.getHeaders() });
  }

  acceptNegociation(negoId: string, acceptedPrice: number): Observable<Negociation> {
    return this.http.post<Negociation>(`${this.apiUrl}/${negoId}/accept`, { acceptedPrice }, { headers: this.getHeaders() });
  }

  createNegociation(negociation: any): Observable<Negociation> {
    return this.http.post<Negociation>(this.apiUrl, negociation, { headers: this.getHeaders() });
  }

  saveMessage(message: MessageNegociation): Observable<MessageNegociation> {
    return this.http.post<MessageNegociation>(`${this.apiUrl}/messages`, message, { headers: this.getHeaders() });
  }

  ajusterNegociation(nego: Negociation, prixPropose: number, history: number[], prixPlancher: number): Observable<any> {
    const payload = {
      negociationId: nego.id,
      prixActuel: nego.prixFinal,
      prixMin: prixPlancher, // Real prixPlancher from the product database
      prixPropose: prixPropose,
      roundActuel: (nego.rounds || 0) + 1,
      roundsMax: 5,
      historiqueOffres: history
    };
    console.log('[NegotiationService] Payload envoyé:', JSON.stringify(payload));
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/nego/manual`, payload, { headers: this.getHeaders() });
  }

  deleteNegociation(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`, { headers: this.getHeaders() });
  }

  // --- AgentAcheteur methods ---

  askAcheteurChat(message: string, sessionId: string): Observable<any> {
    const payload = { message, sessionId };
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/acheteur/chat`, payload, { headers: this.getHeaders() });
  }

  startAcheteurNegoAuto(nego: Negociation, prixCible: number, prixPlancher: number, sessionId: string): Observable<any> {
    const payload = {
      negociationId: nego.id,
      prixActuel: nego.prixFinal || nego.prixInitial,
      prixMin: prixPlancher,
      budget: prixCible,
      roundActuel: (nego.rounds || 0) + 1,
      roundsMax: 5,
      sessionId: sessionId
    };
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/nego/auto/start`, payload, { headers: this.getHeaders() });
  }

  sendAcheteurNegoMessage(message: string, negoId: string, sessionId: string): Observable<any> {
    const payload = { message, negociationId: negoId, sessionId };
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/acheteur/nego/message`, payload, { headers: this.getHeaders() });
  }

  commenterNegociation(payload: any): Observable<any> {
    return this.http.post<any>(`${API_CONFIG.baseUrl}/agent/acheteur/commenter`, payload, { headers: this.getHeaders() });
  }
}
