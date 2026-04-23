import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditService, Audit } from '../../core/services/audit.service';

@Component({
  selector: 'app-supervisor-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './supervisor-dashboard.html',
  styleUrl: './supervisor-dashboard.css'
})
export class SupervisorDashboardComponent implements OnInit {
  audits: Audit[] = [];
  criticalCount = 0;

  private auditService = inject(AuditService);

  ngOnInit() {
    this.refreshAudits();
  }

  refreshAudits() {
    this.auditService.getAudits().subscribe({
      next: a => {
        this.audits = a;
        this.criticalCount = a.filter(x => x.severite === 'CRITICAL').length;
      },
      error: err => console.error(err)
    });
  }

  getCountBySeverity(severity: string): number {
    return this.audits.filter(a => a.severite === severity).length;
  }
}
