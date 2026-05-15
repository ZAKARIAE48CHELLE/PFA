import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NgxPaginationModule } from 'ngx-pagination';
import { ErrorDashboardService, SystemError } from '../../../core/services/error-dashboard.service';
import { API_CONFIG } from '../../../core/config/api.config';
import SockJS from 'sockjs-client';
import * as Stomp from 'stompjs';

import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-errors-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxPaginationModule, RouterModule],
  templateUrl: './errors-dashboard.html',
  styleUrl: './errors-dashboard.css'
})
export class ErrorsDashboardComponent implements OnInit, OnDestroy {
  
  private errorService = inject(ErrorDashboardService);

  // Core datasets
  errors: SystemError[] = [];
  filteredErrors: SystemError[] = [];
  
  // Real-time WebSocket Client reference
  private stompClient: any;

  // Filters & Pagination
  selectedSeverityFilter: string = 'ALL';
  selectedServiceFilter: string = 'ALL';
  showResolved: boolean = false;
  p: number = 1;

  // Metric Counters
  stats = {
    totalUnresolved: 0,
    criticalUnresolved: 0,
    highUnresolved: 0,
    mediumUnresolved: 0,
    lowUnresolved: 0
  };

  // Live alerts list (transient visual alerts)
  activeAlerts: any[] = [];

  ngOnInit(): void {
    this.loadAllData();
    this.connectWebSocket();
  }

  ngOnDestroy(): void {
    this.disconnectWebSocket();
  }

  loadAllData(): void {
    this.loadStats();
    this.loadErrors();
  }

  loadStats(): void {
    this.errorService.getStats().subscribe({
      next: (s) => this.stats = s,
      error: (e) => console.error('[ErrorsDashboard] Failed to load stats:', e)
    });
  }

  loadErrors(): void {
    const observable = this.showResolved 
      ? this.errorService.getAllErrors() 
      : this.errorService.getUnresolvedErrors();

    observable.subscribe({
      next: (list) => {
        this.errors = list;
        this.applyFilters();
      },
      error: (e) => console.error('[ErrorsDashboard] Failed to load errors:', e)
    });
  }

  applyFilters(): void {
    this.filteredErrors = this.errors.filter(err => {
      const matchesSeverity = this.selectedSeverityFilter === 'ALL' || err.severity === this.selectedSeverityFilter;
      const matchesService = this.selectedServiceFilter === 'ALL' || err.service === this.selectedServiceFilter;
      return matchesSeverity && matchesService;
    });
    this.p = 1; // Reset to page 1
  }

  toggleShowResolved(): void {
    this.loadErrors();
  }

  resolveError(id: string): void {
    this.errorService.resolveError(id).subscribe({
      next: () => {
        this.loadAllData();
        this.removeAlertById(id);
      },
      error: (e) => alert('Failed to resolve error: ' + e.message)
    });
  }

  // --- REAL-TIME WEBSOCKET (STOMP) ---

  private connectWebSocket(): void {
    try {
      // API_CONFIG.baseUrl resolves to http://localhost:8080/ws
      const wsEndpoint = `${API_CONFIG.baseUrl}/ws`;
      const socket = new SockJS(wsEndpoint);
      this.stompClient = Stomp.over(socket);

      // Disable noisy debug frame logs in console
      this.stompClient.debug = null;

      this.stompClient.connect({}, () => {
        console.log('[WebSocket] Connected successfully to Central Audit Store.');

        this.stompClient.subscribe('/topic/errors', (frame: any) => {
          const errorItem: SystemError = JSON.parse(frame.body);
          this.handleIncomingSocketError(errorItem);
        });
      }, (error: any) => {
        console.warn('[WebSocket] Dropped connection. Attempting to reconnect in 5s...', error);
        setTimeout(() => this.connectWebSocket(), 5000);
      });

    } catch (e) {
      console.error('[WebSocket] Initialization Crash:', e);
    }
  }

  private handleIncomingSocketError(error: SystemError): void {
    // Add to head of main lists
    this.errors.unshift(error);
    this.applyFilters();
    
    // Re-increment count matching incoming telemetry
    this.stats.totalUnresolved++;
    if (error.severity === 'CRITICAL') this.stats.criticalUnresolved++;
    if (error.severity === 'HIGH') this.stats.highUnresolved++;

    // Add a visual toast notification at the top of viewport
    this.pushToastAlert(error);
    this.playAlertSound();
  }

  private pushToastAlert(error: SystemError): void {
    const toast = {
      id: error.id,
      severity: error.severity,
      service: error.service,
      message: error.message,
      createdAt: new Date()
    };
    this.activeAlerts.push(toast);

    // Automatically expire transient alert toast after 10 seconds
    setTimeout(() => {
      this.removeAlertById(toast.id);
    }, 10000);
  }

  removeAlertById(id: string): void {
    this.activeAlerts = this.activeAlerts.filter(a => a.id !== id);
  }

  private playAlertSound(): void {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      osc.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioContext.currentTime); // A5 pitch
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      
      osc.start();
      gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.8);
      osc.stop(audioContext.currentTime + 0.8);
    } catch (e) {
      // Handled gracefully if browser disables automated audio contexts
    }
  }

  private disconnectWebSocket(): void {
    if (this.stompClient && this.stompClient.connected) {
      this.stompClient.disconnect(() => {
        console.log('[WebSocket] Disconnected cleaner.');
      });
    }
  }

  // Utility formatting
  getSeverityColor(sev: string): string {
    switch (sev) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MEDIUM': return '#f59e0b';
      case 'LOW': return '#3b82f6';
      default: return '#64748b';
    }
  }
}
