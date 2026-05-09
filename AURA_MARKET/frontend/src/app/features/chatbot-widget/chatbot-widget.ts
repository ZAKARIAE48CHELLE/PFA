import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { API_CONFIG } from '../../core/config/api.config';

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  type?: string;
  produits?: any[];
  commandes?: any[];
  timestamp: Date;
}

@Component({
  selector: 'app-chatbot-widget',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './chatbot-widget.html',
  styleUrl: './chatbot-widget.css'
})
export class ChatbotWidgetComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollMe') private myScrollContainer?: ElementRef;

  isOpen = false;
  isTyping = false;
  userMessage = '';
  messages: ChatMessage[] = [];
  sessionId: string;
  private needsScroll = false;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router
  ) {
    this.sessionId = Math.random().toString(36).substring(7);
  }

  ngOnInit() {
    // Initial greeting
    this.messages.push({
      role: 'agent',
      content: 'Bonjour ! Je suis Aura, votre assistant IA. Comment puis-je vous aider aujourd\'hui ?',
      timestamp: new Date()
    });
  }

  ngAfterViewChecked() {
    if (this.needsScroll) {
      this.scrollToBottom();
      this.needsScroll = false;
    }
  }

  scrollToBottom(): void {
    try {
      if (this.myScrollContainer) {
        this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight;
      }
    } catch (err) { }
  }

  toggleChat() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.needsScroll = true;
      if (this.messages.length === 1) {
        this.addSuggestion();
      }
    }
  }

  private addSuggestion() {
    const route = this.router.url;
    if (route.includes('/cart')) {
      this.messages.push({
        role: 'agent',
        content: 'Je vois que vous avez des articles dans votre panier. Voulez-vous que je vous aide à négocier un meilleur prix ?',
        timestamp: new Date()
      });
    } else if (route.includes('/list-produit')) {
      this.messages.push({
        role: 'agent',
        content: 'Vous cherchez quelque chose de particulier ? Je peux filtrer les meilleures offres pour vous.',
        timestamp: new Date()
      });
    }
  }

  sendMessage() {
    if (!this.userMessage.trim()) return;

    const msg = this.userMessage;
    this.messages.push({
      role: 'user',
      content: msg,
      timestamp: new Date()
    });
    this.userMessage = '';
    this.isTyping = true;
    this.needsScroll = true;

    const payload = {
      sessionId: this.sessionId,
      message: msg,
      route: this.router.url,
      userId: this.authService.currentUserValue?.id
    };

    this.http.post<any>(`${API_CONFIG.baseUrl}/agent/chat/navigate`, payload).subscribe({
      next: (res) => {
        this.isTyping = false;
        this.messages.push({
          role: 'agent',
          content: res.reponse || 'Désolé, je n\'ai pas compris.',
          type: res.type,
          produits: res.produits,
          commandes: res.commandes,
          timestamp: new Date()
        });
        this.needsScroll = true;
      },
      error: () => {
        this.isTyping = false;
        this.messages.push({
          role: 'agent',
          content: 'Oups, je rencontre un problème technique. Réessayez plus tard.',
          timestamp: new Date()
        });
      }
    });
  }

  quickAction(action: string) {
    this.userMessage = action;
    this.sendMessage();
  }
}
