import { ErrorHandler, Injectable, Injector } from '@angular/core';
import { ErrorDashboardService } from '../services/error-dashboard.service';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {

  constructor(private injector: Injector) {}

  handleError(error: any): void {
    // Print locally to dev console as usual
    console.error('[AuraMarket GlobalError Catch]', error);

    try {
      // Use Injector dynamically because GlobalErrorHandler is created before ErrorDashboardService
      const errorService = this.injector.get(ErrorDashboardService);
      
      const message = error?.message || error?.toString() || 'Unknown UI Exception';
      const stack = error?.stack || '';
      const currentUrl = window.location.pathname + window.location.search;

      // Asynchronously emit telemetry directly back to the microservices log center
      errorService.reportFrontendError({
        service: 'angular-frontend',
        errorType: 'FRONTEND_ERROR',
        message: message,
        stackTrace: stack,
        endpoint: currentUrl,
        severity: 'LOW'
      }).subscribe({
        error: (e) => console.warn('[GlobalErrorHandler] Failed to pipe UI error to backend audit store:', e.message)
      });

    } catch (injectorError) {
      console.error('[GlobalErrorHandler] Critical self failure:', injectorError);
    }
  }
}
