import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../config/api.config';
import { AuthService } from './auth.service';

export interface Produit {
  id: string;
  titre: string;
  description: string;
  prix: number;
  prixMin: number;
  categorie: string;
  imageUrl: string;
  stock: number;
  statut: string;
  datePublication: string;
  vendeurId: string;
  prixOffre?: number;
}

export interface Offre {
  id: string;
  titre: string;
  description: string;
  prixPropose: number;
  prixFinal: number;
  statut: string;
  dateCreation: string;
  dateExpiration: string;
  dateDebut?: string;
  dateFin?: string;
  pourcentageDiscount?: number;
  produitId: string;
  acheteurId: string;
  agentGenere: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private apiUrl = API_CONFIG.baseUrl;

  constructor(private http: HttpClient, private authService: AuthService) { }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Authorization': `Bearer ${this.authService.getToken()}`,
      'ngrok-skip-browser-warning': 'true'
    });
  }

  getProduits(): Observable<Produit[]> {
    return this.http.get<Produit[]>(`${this.apiUrl}/products`, { headers: this.getHeaders() });
  }
  getProduitById(id: string): Observable<Produit> {
    return this.http.get<Produit>(`${this.apiUrl}/products/${id}`, { headers: this.getHeaders() });
  }

  createProduit(produit: any): Observable<Produit> {
    return this.http.post<Produit>(`${this.apiUrl}/products`, produit, { headers: this.getHeaders() });
  }

  updateProduit(id: string, produit: any): Observable<Produit> {
    return this.http.put<Produit>(`${this.apiUrl}/products/${id}`, produit, { headers: this.getHeaders() });
  }

  deleteProduit(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/products/${id}`, { headers: this.getHeaders() });
  }

  getOffres(): Observable<Offre[]> {
    return this.http.get<Offre[]>(`${this.apiUrl}/offers`, { headers: this.getHeaders() });
  }

  createOffre(offre: any): Observable<Offre> {
    return this.http.post<Offre>(`${this.apiUrl}/offers`, offre, { headers: this.getHeaders() });
  }

  updateOffre(id: string, offre: any): Observable<Offre> {
    return this.http.put<Offre>(`${this.apiUrl}/offers/${id}`, offre, { headers: this.getHeaders() });
  }

  deleteOffre(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/offers/${id}`, { headers: this.getHeaders() });
  }

  genererOffreAgent(p: Produit): Observable<any> {
    const payload = {
      produitId: p.id,
      titre: p.titre,
      prixBase: p.prix,
      prixMin: p.prixMin,
      categorie: p.categorie,
      plateforme: 'amazon'
    };
    return this.http.post<any>(`${this.apiUrl}/agent/offre/generer`, payload, { headers: this.getHeaders() });
  }

  verifierSecurite(payload: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/agent/securite/verifier`, payload, { headers: this.getHeaders() });
  }

  accepterOffre(offreId: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/offers/${offreId}/accepter`, {}, { headers: this.getHeaders() });
  }

  payerOffre(offreId: string, request: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/offers/${offreId}/payer`, request, { headers: this.getHeaders() });
  }

  getCommande(commandeId: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/commandes/${commandeId}`, { headers: this.getHeaders() });
  }

  getCommandesByAcheteur(acheteurId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/commandes/acheteur/${acheteurId}`, { headers: this.getHeaders() });
  }

  getCommandesByVendeur(vendeurId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/commandes/vendeur/${vendeurId}`, { headers: this.getHeaders() });
  }

  getAllCommandes(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/commandes`, { headers: this.getHeaders() });
  }

  getComments(produitId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/products/${produitId}/comments`, { headers: this.getHeaders() });
  }

  addComment(produitId: string, comment: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/products/${produitId}/comments`, comment, { headers: this.getHeaders() });
  }
  
  getOffresByProduit(produitId: string): Observable<Offre[]> {
    return this.http.get<Offre[]>(`${this.apiUrl}/products/${produitId}/offers`, { headers: this.getHeaders() });
  }
}
