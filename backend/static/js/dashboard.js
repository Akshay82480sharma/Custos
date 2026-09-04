/**
 * CUSTOS Dashboard - Real-time scan progress and DOM updates
 */

class CUSTOSDashboard {
  constructor() {
    this.scanButton = document.getElementById('run-custos-btn');
    this.progressContainer = document.getElementById('scan-progress');
    this.progressBar = document.getElementById('progress-bar');
    this.progressText = document.getElementById('progress-text');
    this.progressStage = document.getElementById('progress-stage');
    this.activityTableBody = document.querySelector('#activity-table tbody');
    this.metricsContainer = document.querySelector('.metrics');
    this.errorContainer = document.getElementById('scan-error');
    this.retryButton = document.getElementById('retry-btn');
    this.isScanning = false;
    this.lastError = null;
    this.init();
  }

  init() {
    if (this.scanButton) {
      this.scanButton.addEventListener('click', () => this.startScan());
    }
    if (this.retryButton) {
      this.retryButton.addEventListener('click', () => this.retryScan());
    }
  }

  startScan() {
    if (this.isScanning) return;
    
    this.isScanning = true;
    this.lastError = null;
    this.scanButton.disabled = true;
    this.scanButton.innerHTML = '<span class="spinner"></span> Scanning...';
    this.scanButton.classList.add('scanning');
    
    this.hideError();
    this.showProgress();
    this.updateProgress(0, 'Initializing...', 'Starting pipeline...');
    
    // Use fetch with streaming to get SSE updates
    fetch('/api/scan/stream')
      .then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        const readStream = () => {
          reader.read().then(({ done, value }) => {
            if (done) {
              this.onScanComplete();
              return;
            }
            
            const text = decoder.decode(value);
            const lines = text.split('\n');
            
            lines.forEach(line => {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  this.handleProgressUpdate(data);
                } catch (e) {
                  console.error('Failed to parse SSE data:', e);
                }
              }
            });
            
            readStream();
          });
        };
        
        readStream();
      })
      .catch(error => {
        console.error('Scan failed:', error);
        this.onScanError('Network error: ' + error.message);
      });
  }

  retryScan() {
    this.startScan();
  }

  showProgress() {
    if (this.progressContainer) {
      this.progressContainer.style.display = 'block';
    }
  }

  hideProgress() {
    if (this.progressContainer) {
      this.progressContainer.style.display = 'none';
    }
  }

  showError(message, failedAt) {
    if (this.errorContainer) {
      this.errorContainer.style.display = 'block';
      this.errorContainer.innerHTML = `
        <div class="error-content">
          <span class="error-icon">⚠️</span>
          <div class="error-details">
            <strong>Scan failed</strong>
            <p>${message}</p>
            ${failedAt ? `<small>Failed at: ${failedAt}</small>` : ''}
          </div>
          <button id="retry-btn" class="retry-btn">Retry</button>
        </div>
      `;
      // Re-attach retry button listener
      this.retryButton = document.getElementById('retry-btn');
      if (this.retryButton) {
        this.retryButton.addEventListener('click', () => this.retryScan());
      }
    }
  }

  hideError() {
    if (this.errorContainer) {
      this.errorContainer.style.display = 'none';
    }
  }

  updateProgress(percent, stage, message) {
    if (this.progressBar) {
      this.progressBar.style.width = `${percent}%`;
    }
    if (this.progressStage) {
      this.progressStage.textContent = stage;
    }
    if (this.progressText && message) {
      this.progressText.textContent = message;
    }
  }

  handleProgressUpdate(data) {
    if (data.status === 'starting') {
      this.updateProgress(5, 'Starting...', data.message);
    } else if (data.status === 'running') {
      const percent = Math.min(data.progress + 10, 95); // Cap at 95% until complete
      const stage = data.stage || 'Processing...';
      this.updateProgress(percent, stage, data.message);
    } else if (data.status === 'ok') {
      this.updateProgress(100, 'Complete', 'All stages completed successfully');
    } else if (data.status === 'already_running') {
      this.onScanError('A scan is already running. Please wait.');
    } else if (data.status === false || data.failed_at) {
      this.onScanError(data.error || 'Unknown error', data.failed_at);
    }
  }

  onScanComplete() {
    this.isScanning = false;
    this.scanButton.disabled = false;
    this.scanButton.innerHTML = '▶ Run Custos';
    this.scanButton.classList.remove('scanning');
    
    this.updateProgress(100, 'Complete', 'Refresh to see results');
    
    if (typeof showToast === 'function') {
      showToast('Pipeline scan completed successfully!', 'success');
    }
    
    // Auto-refresh activity feed after 1 second
    setTimeout(() => {
      this.refreshActivityFeed();
    }, 1000);
    
    // Hide progress after 3 seconds
    setTimeout(() => {
      this.hideProgress();
    }, 3000);
  }

  onScanError(message, failedAt) {
    this.isScanning = false;
    this.lastError = { message, failedAt };
    this.scanButton.disabled = false;
    this.scanButton.innerHTML = '▶ Run Custos';
    this.scanButton.classList.remove('scanning');
    
    this.showError(message, failedAt);
    
    if (typeof showToast === 'function') {
      showToast('Scan failed: ' + message, 'error');
    }
    
    setTimeout(() => {
      this.hideProgress();
    }, 2000);
  }

  refreshActivityFeed() {
    fetch('/api/overview')
      .then(response => response.json())
      .then(data => {
        this.updateMetrics(data.metrics);
        this.updateActivityTable(data.events);
      })
      .catch(error => console.error('Failed to refresh:', error));
  }

  updateMetrics(metrics) {
    if (!this.metricsContainer || !metrics) return;
    
    const articles = this.metricsContainer.querySelectorAll('article');
    const values = [
      metrics.revenue_at_risk,
      metrics.verified_recovered,
      metrics.risk_exposure,
      metrics.growth_potential,
      metrics.finance_exceptions
    ];
    
    articles.forEach((article, index) => {
      if (values[index] !== undefined) {
        const strong = article.querySelector('strong');
        if (strong) {
          if (index < 4) {
            strong.textContent = `₹${values[index].toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
          } else {
            strong.textContent = values[index];
          }
        }
      }
    });
  }

  updateActivityTable(events) {
    if (!this.activityTableBody || !events) return;
    
    if (events.length === 0) {
      this.activityTableBody.innerHTML = '<tr><td colspan="5">No merchant data yet. Run a scan to load demo data.</td></tr>';
      return;
    }
    
    this.activityTableBody.innerHTML = events.map(event => `
      <tr onclick="location.href='/demo/${event.id}'">
        <td>${event.source_id}</td>
        <td><span class="status ${event.status}">${event.status}</span></td>
        <td>₹${event.amount_inr.toLocaleString('en-IN')}</td>
        <td>${event.recommended_action || '—'}</td>
        <td>${event.policy_decision || 'Pending'}</td>
      </tr>
    `).join('');
  }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new CUSTOSDashboard();
});
