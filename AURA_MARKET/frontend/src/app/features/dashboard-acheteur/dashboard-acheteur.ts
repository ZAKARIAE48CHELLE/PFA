import { Component, OnInit, inject, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { NegotiationService, Negociation, MessageNegociation } from '../../core/services/negotiation.service';
import { CartService } from '../../core/services/cart.service';
import { Router, RouterModule } from '@angular/router';

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
  statusMessage = '';
  statusType: 'success' | 'danger' = 'success';
  
  // Buyer Agent states
  autoNegoInProgress = false;
  autoNegoTarget: number = 0;
  aiSuggestion: string | undefined;
  sessionId = 'session_' + Math.random().toString(36).substring(7);

  private negoService = inject(NegotiationService);
  private productService = inject(ProductService);
  private cartService = inject(CartService);
  private router = inject(Router);
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
      if (this.selectedNego) {
        const updated = n.find(x => x.id === this.selectedNego!.id);
        if (updated) {
          this.selectedNego = updated;
        }
      } else if (n.length > 0) {
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

    const userMsg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'ACHETEUR',
      content: `Je propose un prix de ${price} MAD`,
      price: price
    };

    this.negoService.saveMessage(userMsg).subscribe({
      next: () => {
        if (this.selectedNego) {
          this.selectedNego.rounds = (this.selectedNego.rounds || 0) + 1;
        }
        this.loadMessages(this.selectedNego!.id);
        
        const priceHistory = this.messages
          .filter(m => m.sender === 'ACHETEUR')
          .map(m => m.price);
        
        const produit = this.getProduitForNego(this.selectedNego!.produitId);
        const prixMin = produit?.prixMin || this.selectedNego!.prixInitial * 0.6;

        this.negoService.ajusterNegociation(this.selectedNego!, price, priceHistory, prixMin).subscribe({
          next: (res) => {
            const commentaryPayload = {
              nouveauPrix: res.nouveauPrix,
              prixActuel: this.selectedNego!.prixFinal,
              buyerBehavior: res.buyerBehavior,
              round: this.selectedNego!.rounds
            };

            this.negoService.commenterNegociation(commentaryPayload).subscribe({
              next: (commentRes) => {
                const agentMsg: MessageNegociation = {
                  negociationId: this.selectedNego!.id,
                  sender: 'AGENT',
                  content: commentRes.message,
                  price: res.nouveauPrix
                };
                this.negoService.saveMessage(agentMsg).subscribe(() => {
                  this.loadMessages(this.selectedNego!.id);
                  this.isSending = false;
                  this.loadData();
                  this.selectedNego!.prixFinal = res.nouveauPrix;
                });
              },
              error: () => {
                const agentMsg: MessageNegociation = {
                  negociationId: this.selectedNego!.id,
                  sender: 'AGENT',
                  content: `Ma contre-proposition est de ${res.nouveauPrix} MAD.`,
                  price: res.nouveauPrix
                };
                this.negoService.saveMessage(agentMsg).subscribe(() => {
                  this.loadMessages(this.selectedNego!.id);
                  this.isSending = false;
                  this.loadData();
                });
              }
            });
          },
          error: (err) => {
            console.error('Agent adjustment error:', err);
            this.showStatus("L'agent n'a pas pu répondre.", 'danger');
            this.isSending = false;
          }
        });
      }
    });
  }

  startAutoNego() {
    if (!this.selectedNego || !this.newMessagePrice || this.isSending) return;
    
    const target = this.newMessagePrice;
    this.newMessagePrice = undefined;
    this.isSending = true;
    this.autoNegoInProgress = true;
    this.autoNegoTarget = target;

    const userMsg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'ACHETEUR',
      content: `🤖 Négociation AUTO lancée — budget: ${target} MAD. L'IA négocie pour moi.`,
      price: target
    };

    this.negoService.saveMessage(userMsg).subscribe(() => {
      this.loadMessages(this.selectedNego!.id);
      
      const produit = this.getProduitForNego(this.selectedNego!.produitId);
      const prixMin = produit?.prixMin || this.selectedNego!.prixInitial * 0.6;

      this.negoService.startAcheteurNegoAuto(this.selectedNego!, target, prixMin, this.sessionId).subscribe({
        next: (res) => {
          this.autoNegoInProgress = false;

          const agentMsg: MessageNegociation = {
            negociationId: this.selectedNego!.id,
            sender: 'AGENT',
            content: res.reponse,
            price: res.prixAccord || res.prixFinal || this.selectedNego!.prixFinal
          };
          
          this.negoService.saveMessage(agentMsg).subscribe(() => {
            this.loadMessages(this.selectedNego!.id);
            this.isSending = false;
            
            if (res.prixFinal) {
              this.selectedNego!.prixFinal = res.prixFinal;
            }

            if (res.accordTrouve) {
              this.selectedNego!.prixFinal = res.prixAccord;
              this.showStatus(`✅ Accord trouvé à ${res.prixAccord} MAD !`);
            } else {
              this.showStatus(`Meilleure offre du vendeur: ${res.prixFinal} MAD. Vous pouvez accepter ou continuer.`, 'danger');
            }
            this.loadData();
          });
        },
        error: (err) => {
          this.autoNegoInProgress = false;
          this.showStatus("L'assistant n'a pas pu démarrer la négociation.", 'danger');
          this.isSending = false;
        }
      });
    });
  }

  askAISuggestion() {
    if (!this.selectedNego || this.isSending) return;
    
    this.isSending = true;
    const lastMsg = this.messages.length > 0 ? this.messages[this.messages.length-1].content : "Début de négo";

    this.negoService.sendAcheteurNegoMessage(lastMsg, this.selectedNego.id, this.sessionId).subscribe({
      next: (res) => {
        this.aiSuggestion = res.reponse;
        this.isSending = false;
      },
      error: () => {
        this.showStatus("Impossible de contacter l'assistant IA.", 'danger');
        this.isSending = false;
      }
    });
  }

  useAISuggestion() {
    if (!this.aiSuggestion) return;
    
    // Attempt to extract a price like "1200 MAD" or "1200.50 MAD" or just "1200"
    const match = this.aiSuggestion.match(/(\d+(?:[.,]\d+)?)/);
    if (match) {
      this.newMessagePrice = parseFloat(match[1].replace(',', '.'));
      this.showStatus("Prix suggéré appliqué !");
    }
    this.aiSuggestion = undefined;
  }

  deleteNego(event: Event, id: string) {
    event.stopPropagation();
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
    
    const p = this.getProduitForNego(this.selectedNego.produitId);
    if (!p) return;

    this.isSending = true;
    this.showStatus("Acceptation en cours...");

    const negotiatedProduct = { 
      ...p, 
      prixOffre: this.selectedNego.prixFinal 
    };

    this.cartService.addToCart(negotiatedProduct);
    
    this.isSending = false;
    this.router.navigate(['/checkout']);
  }

  selectOfferFromHistory(price: number) {
    if (this.selectedNego) {
      this.selectedNego.prixFinal = price;
    }
  }
}
