import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditService, Audit } from '../../core/services/audit.service';
import { ProductService } from '../../core/services/product.service';
import { NgxPaginationModule } from 'ngx-pagination';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-supervisor-dashboard',
  standalone: true,
  imports: [CommonModule, BaseChartDirective, NgxPaginationModule],
  templateUrl: './supervisor-dashboard.html',
  styleUrl: './supervisor-dashboard.css'
})
export class SupervisorDashboardComponent implements OnInit {
  audits: Audit[] = [];
  criticalCount = 0;

  // Chart configs
  public severityChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: ['INFO', 'WARNING', 'CRITICAL'],
    datasets: [{ data: [0, 0, 0], backgroundColor: ['#3b82f6', '#f59e0b', '#ef4444'], hoverOffset: 4 }]
  };
  public severityChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { color: '#64748b' } } },
    cutout: '70%'
  };

  public agentChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [{ data: [], label: 'Audits par Agent', backgroundColor: '#6366f1', borderRadius: 6 }]
  };
  public agentChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    scales: { 
      y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
      x: { grid: { display: false }, ticks: { color: '#64748b' } }
    },
    plugins: { legend: { display: false } }
  };

  public topSellersChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [{ data: [], label: 'Revenus par Vendeur (MAD)', backgroundColor: '#10b981', borderRadius: 6 }]
  };
  public topSellersChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    scales: { 
      y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
      x: { grid: { display: false }, ticks: { color: '#64748b' }, display: false }
    },
    plugins: { legend: { display: false } }
  };

  private auditService = inject(AuditService);
  private productService = inject(ProductService);

  totalSales: number = 0;
  commandes: any[] = [];
  activeTab: 'overview' | 'audit' = 'overview';
  p: number = 1;

  ngOnInit() {
    this.refreshData();
  }

  refreshData() {
    this.auditService.getAudits().subscribe({
      next: a => {
        this.audits = a;
        this.criticalCount = a.filter(x => x.severite === 'CRITICAL').length;
        this.updateAuditCharts();
      },
      error: err => console.error(err)
    });

    this.productService.getAllCommandes().subscribe({
      next: c => {
        this.commandes = c;
        this.updateBusinessMetrics();
      },
      error: err => console.error(err)
    });
  }

  updateBusinessMetrics() {
    this.totalSales = this.commandes.reduce((sum, c) => sum + (c.prixFinal || 0), 0);

    const sellerRevenue: { [key: string]: number } = {};
    this.commandes.forEach(c => {
      const vid = c.vendeurId || 'Plateforme';
      sellerRevenue[vid] = (sellerRevenue[vid] || 0) + (c.prixFinal || 0);
    });

    // Sort by revenue descending
    const sortedSellers = Object.keys(sellerRevenue).sort((a, b) => sellerRevenue[b] - sellerRevenue[a]).slice(0, 5); // top 5
    
    this.topSellersChartData = {
      labels: sortedSellers,
      datasets: [{ data: sortedSellers.map(s => sellerRevenue[s]), label: 'Revenus (MAD)', backgroundColor: '#10b981', borderRadius: 6 }]
    };
  }

  updateAuditCharts() {
    // Severity Chart
    const info = this.getCountBySeverity('INFO');
    const warning = this.getCountBySeverity('WARNING');
    const critical = this.getCountBySeverity('CRITICAL');
    
    // Create new objects to trigger Angular change detection for ng2-charts
    this.severityChartData = {
      labels: ['INFO', 'WARNING', 'CRITICAL'],
      datasets: [{ data: [info, warning, critical], backgroundColor: ['#3b82f6', '#f59e0b', '#ef4444'], hoverOffset: 4 }]
    };

    // Agent Chart
    const agentCounts: { [key: string]: number } = {};
    this.audits.forEach(a => {
      const agentName = a.agentSource || 'Inconnu';
      agentCounts[agentName] = (agentCounts[agentName] || 0) + 1;
    });

    this.agentChartData = {
      labels: Object.keys(agentCounts),
      datasets: [{ data: Object.values(agentCounts), label: 'Audits par Agent', backgroundColor: '#6366f1', borderRadius: 6 }]
    };
  }

  getCountBySeverity(severity: string): number {
    return this.audits.filter(a => a.severite === severity).length;
  }
}
