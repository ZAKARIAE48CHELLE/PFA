import { Component, OnInit, inject, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { NegotiationService, Negociation, MessageNegociation } from '../../core/services/negotiation.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-dashboard-acheteur',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './dashboard-acheteur.html',
  styleUrl: './dashboard-acheteur.css'
})
export class DashboardAcheteurComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollMe') private myScrollContainer?: ElementRef;
  
  negociations: Negociation[] = [];
  produits: Produit[] = [];
  selectedNego?: Negociation;
  isSending = false;
  showAcceptModal = false;
  statusMessage = '';
  statusType: 'success' | 'danger' = 'success';

  private negoService = inject(NegotiationService);
  private productService = inject(ProductService);
  messages: MessageNegociation[] = [];
  newMessagePrice: number | undefined;
  ngOnInit() {
    this.loadData();
  }

  showStatus(msg: string, type: 'success' | 'danger' = 'success') {
    this.statusMessage = msg;
    this.statusType = type;
    setTimeout(() => this.statusMessage = '', 5000);
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      if (this.myScrollContainer) {
        this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight;
      }
    } catch (err) { }
  }

  loadData() {
    this.negoService.getNegociations().subscribe(n => {
      this.negociations = n;
      if (n.length > 0 && !this.selectedNego) {
        this.selectNego(n[0]);
      }
    });
    this.productService.getProduits().subscribe(p => this.produits = p);
  }

  selectNego(nego: Negociation) {
    this.selectedNego = nego;
    this.loadMessages(nego.id);
  }

  loadMessages(negoId: string) {
    this.negoService.getMessages(negoId).subscribe(m => {
      this.messages = m;
    });
  }

  getProduitForNego(produitId: string | undefined): Produit | undefined {
    if (!produitId) return undefined;
    return this.produits.find(p => p.id === produitId);
  }

  sendMessage() {
    if (!this.selectedNego || !this.newMessagePrice || this.isSending) return;
    
    const price = this.newMessagePrice;
    this.newMessagePrice = undefined;
    this.isSending = true;

    // 1. Save User Message
    const userMsg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'ACHETEUR',
      content: `Je propose un prix de ${price} €`,
      price: price
    };

    this.negoService.saveMessage(userMsg).subscribe({
      next: () => {
        this.loadMessages(this.selectedNego!.id);
        
        // 2. Get Agent Response
        const priceHistory = this.messages
          .filter(m => m.sender === 'ACHETEUR')
          .map(m => m.price);
        
        this.negoService.ajusterNegociation(this.selectedNego!, price, priceHistory).subscribe({
          next: (res) => {
            // 3. Save Agent Message
            const agentMsg: MessageNegociation = {
              negociationId: this.selectedNego!.id,
              sender: 'AGENT',
              content: `Ma contre-proposition est de ${res.nouveauPrix} €.`,
              price: res.nouveauPrix
            };
            this.negoService.saveMessage(agentMsg).subscribe(() => {
              this.loadMessages(this.selectedNego!.id);
              this.isSending = false;
              this.loadData(); // Refresh rounds
            });
          },
          error: (err) => {
            console.error('Agent adjustment error:', err);
            this.showStatus(err.error?.error || "L'agent n'a pas pu répondre.", 'danger');
            this.isSending = false;
          }
        });
      },
      error: (err) => {
        console.error('Save message error:', err);
        this.showStatus("Erreur lors de l'envoi du message.", 'danger');
        this.isSending = false;
      }
    });
  }

  deleteNego(event: Event, id: string) {
    event.stopPropagation();
    // Simplified delete for now (could also use a modal, but let's at least remove native confirm for consistency if possible)
    // Here I'll just do it directly or add another confirmation state
    this.negoService.deleteNegociation(id).subscribe(() => {
      this.showStatus('Négociation supprimée');
      this.loadData();
      if (this.selectedNego?.id === id) {
        this.selectedNego = undefined;
        this.messages = [];
      }
    });
  }

  accepterOffre() {
    if (!this.selectedNego || this.isSending) return;
    this.showAcceptModal = true;
  }

  closeModal() {
    this.showAcceptModal = false;
  }

  getAgentOffers(): MessageNegociation[] {
    const uniquePrices = new Set<number>();
    return this.messages
      .filter((m: MessageNegociation) => m.sender === 'AGENT' && m.price > 0)
      .filter((m: MessageNegociation) => {
        if (uniquePrices.has(m.price)) return false;
        uniquePrices.add(m.price);
        return true;
      })
      .reverse();
  }

  selectOfferFromHistory(price: number) {
    if (this.selectedNego) {
      this.selectedNego.prixFinal = price;
    }
  }

  confirmAcceptation() {
    if (!this.selectedNego || this.isSending) return;
    
    const p = this.getProduitForNego(this.selectedNego.produitId);
    if (!p) return;

    this.isSending = true;
    
    const offreData = {
      titre: `Offre pour ${p.titre}`,
      description: `Négociation finalisée pour le produit ${p.titre}`,
      prixPropose: this.selectedNego.prixFinal,
      produitId: p.id,
      acheteurId: this.selectedNego.acheteurId,
      agentGenere: true
    };

    // 1. Create a formal Offre
    this.productService.createOffre(offreData).subscribe({
      next: (offre) => {
        // 2. Accept the offer
        this.productService.accepterOffre(offre.id).subscribe({
          next: () => {
            // 3. Simulate Payment
            const payRequest = {
              methode: 'CARTE',
              montant: offre.prixPropose
            };
            
            this.productService.payerOffre(offre.id, payRequest).subscribe({
              next: (res) => {
                this.showStatus(`Payé ! Commande ${res.commande.reference} générée.`);
                this.isSending = false;
                this.showAcceptModal = false;
                
                this.negoService.deleteNegociation(this.selectedNego!.id).subscribe(() => {
                  this.loadData();
                  this.selectedNego = undefined;
                  this.messages = [];
                });
              },
              error: (err) => {
                console.error('Payment error:', err);
                const msg = err.error?.message || "Échec du paiement simulation.";
                this.showStatus(msg, 'danger');
                this.isSending = false;
              }
            });
          },
          error: (err) => {
            console.error('Validation error:', err);
            const msg = err.error?.message || "Erreur lors de la validation de l'offre.";
            this.showStatus(msg, 'danger');
            this.isSending = false;
          }
        });
      },
      error: (err) => {
        console.error('Create offer error:', err);
        this.showStatus("Erreur lors de la création de l'offre.", 'danger');
        this.isSending = false;
      }
    });
  }
}
