"""Custom Student-t Hidden Markov Model implementation.

hmmlearn only supports Gaussian emissions, so we implement a custom
Student-t HMM using scipy.stats.multivariate_t for heavier tails,
which is more appropriate for financial returns.
"""

import numpy as np
from scipy import stats
from scipy.special import logsumexp
from typing import Optional, Tuple
import warnings


class StudentTHMM:
    """
    Hidden Markov Model with multivariate Student-t emission distributions.

    The Student-t distribution has heavier tails than the Gaussian,
    making it more robust to outliers common in financial data.

    Parameters
    ----------
    n_components : int
        Number of hidden states.
    df : float
        Degrees of freedom for Student-t distribution.
        Lower values = heavier tails. Typical range: 3-30.
        df -> infinity approaches Gaussian.
    covariance_type : str
        Type of covariance: 'full', 'diag', or 'spherical'.
    n_iter : int
        Maximum number of EM iterations.
    tol : float
        Convergence threshold for EM.
    random_state : int or None
        Random seed for reproducibility.
    """

    def __init__(
        self,
        n_components: int = 7,
        df: float = 5.0,
        covariance_type: str = "full",
        n_iter: int = 100,
        tol: float = 1e-4,
        random_state: Optional[int] = None,
    ):
        self.n_components = n_components
        self.df = df
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.tol = tol
        self.random_state = random_state

        # Model parameters (initialized during fit)
        self.startprob_: Optional[np.ndarray] = None
        self.transmat_: Optional[np.ndarray] = None
        self.means_: Optional[np.ndarray] = None
        self.covars_: Optional[np.ndarray] = None
        self._n_features: Optional[int] = None
        self._is_fitted = False

    def _init_params(self, X: np.ndarray):
        """Initialize model parameters."""
        n_samples, n_features = X.shape
        self._n_features = n_features

        rng = np.random.default_rng(self.random_state)

        # Initialize start probabilities uniformly
        self.startprob_ = np.ones(self.n_components) / self.n_components

        # Initialize transition matrix with diagonal dominance
        self.transmat_ = np.ones((self.n_components, self.n_components))
        self.transmat_ += np.eye(self.n_components) * 10
        self.transmat_ /= self.transmat_.sum(axis=1, keepdims=True)

        # Initialize means using k-means-like initialization
        indices = rng.choice(n_samples, size=self.n_components, replace=False)
        self.means_ = X[indices].copy()

        # Initialize covariances based on data variance
        data_cov = np.cov(X.T)
        if n_features == 1:
            data_cov = np.array([[data_cov]])

        if self.covariance_type == "full":
            self.covars_ = np.array([data_cov.copy() for _ in range(self.n_components)])
        elif self.covariance_type == "diag":
            self.covars_ = np.array([np.diag(data_cov).copy() for _ in range(self.n_components)])
        else:  # spherical
            self.covars_ = np.array([np.mean(np.diag(data_cov))] * self.n_components)

    def _compute_log_likelihood(self, X: np.ndarray) -> np.ndarray:
        """
        Compute log likelihood for each state at each time point.

        Returns log P(x_t | state_i) for all t and i.
        """
        n_samples = X.shape[0]
        log_prob = np.zeros((n_samples, self.n_components))

        for i in range(self.n_components):
            mean = self.means_[i]

            if self.covariance_type == "full":
                cov = self.covars_[i]
            elif self.covariance_type == "diag":
                cov = np.diag(self.covars_[i])
            else:  # spherical
                cov = np.eye(self._n_features) * self.covars_[i]

            # Scale covariance for Student-t (variance = df/(df-2) * sigma^2 for df > 2)
            if self.df > 2:
                scale = cov * (self.df - 2) / self.df
            else:
                scale = cov

            try:
                # Use multivariate Student-t distribution
                dist = stats.multivariate_t(loc=mean, shape=scale, df=self.df)
                log_prob[:, i] = dist.logpdf(X)
            except Exception:
                # Fallback to Gaussian if Student-t fails
                dist = stats.multivariate_normal(mean=mean, cov=cov, allow_singular=True)
                log_prob[:, i] = dist.logpdf(X)

        return log_prob

    def _forward(self, log_prob: np.ndarray) -> Tuple[np.ndarray, float]:
        """Forward algorithm for computing alpha values."""
        n_samples = log_prob.shape[0]
        log_alpha = np.zeros((n_samples, self.n_components))

        # Initialize
        log_alpha[0] = np.log(self.startprob_ + 1e-10) + log_prob[0]

        # Forward pass
        log_transmat = np.log(self.transmat_ + 1e-10)
        for t in range(1, n_samples):
            for j in range(self.n_components):
                log_alpha[t, j] = logsumexp(
                    log_alpha[t - 1] + log_transmat[:, j]
                ) + log_prob[t, j]

        # Log-likelihood
        log_likelihood = logsumexp(log_alpha[-1])

        return log_alpha, log_likelihood

    def _backward(self, log_prob: np.ndarray) -> np.ndarray:
        """Backward algorithm for computing beta values."""
        n_samples = log_prob.shape[0]
        log_beta = np.zeros((n_samples, self.n_components))

        # Initialize (log(1) = 0)
        log_beta[-1] = 0

        # Backward pass
        log_transmat = np.log(self.transmat_ + 1e-10)
        for t in range(n_samples - 2, -1, -1):
            for i in range(self.n_components):
                log_beta[t, i] = logsumexp(
                    log_transmat[i, :] + log_prob[t + 1] + log_beta[t + 1]
                )

        return log_beta

    def _e_step(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """E-step: compute responsibilities (gamma) and transition posteriors (xi)."""
        log_prob = self._compute_log_likelihood(X)
        log_alpha, log_likelihood = self._forward(log_prob)
        log_beta = self._backward(log_prob)

        # Compute gamma (posterior state probabilities)
        log_gamma = log_alpha + log_beta
        log_gamma -= logsumexp(log_gamma, axis=1, keepdims=True)
        gamma = np.exp(log_gamma)

        # Compute xi (posterior transition probabilities)
        n_samples = X.shape[0]
        xi = np.zeros((n_samples - 1, self.n_components, self.n_components))

        log_transmat = np.log(self.transmat_ + 1e-10)
        for t in range(n_samples - 1):
            for i in range(self.n_components):
                for j in range(self.n_components):
                    xi[t, i, j] = (
                        log_alpha[t, i]
                        + log_transmat[i, j]
                        + log_prob[t + 1, j]
                        + log_beta[t + 1, j]
                    )
            xi[t] -= logsumexp(xi[t])

        xi = np.exp(xi)

        return gamma, xi, log_likelihood

    def _m_step(self, X: np.ndarray, gamma: np.ndarray, xi: np.ndarray):
        """M-step: update model parameters."""
        n_samples = X.shape[0]

        # Update start probabilities
        self.startprob_ = gamma[0] / gamma[0].sum()
        self.startprob_ = np.clip(self.startprob_, 1e-10, 1 - 1e-10)
        self.startprob_ /= self.startprob_.sum()

        # Update transition matrix
        xi_sum = xi.sum(axis=0)
        self.transmat_ = xi_sum / xi_sum.sum(axis=1, keepdims=True)
        self.transmat_ = np.clip(self.transmat_, 1e-10, 1 - 1e-10)
        self.transmat_ /= self.transmat_.sum(axis=1, keepdims=True)

        # Update means and covariances with robustness weights
        # For Student-t, we use a weighted update based on Mahalanobis distance
        for i in range(self.n_components):
            # Weighted mean
            gamma_sum = gamma[:, i].sum()
            if gamma_sum < 1e-10:
                continue

            self.means_[i] = (gamma[:, i, np.newaxis] * X).sum(axis=0) / gamma_sum

            # Weighted covariance with Student-t robustness weights
            diff = X - self.means_[i]

            # Compute Mahalanobis distances for robustness weighting
            if self.covariance_type == "full":
                cov = self.covars_[i]
            elif self.covariance_type == "diag":
                cov = np.diag(self.covars_[i])
            else:
                cov = np.eye(self._n_features) * self.covars_[i]

            try:
                cov_inv = np.linalg.inv(cov + np.eye(self._n_features) * 1e-6)
                mahal = np.sum(diff @ cov_inv * diff, axis=1)
            except np.linalg.LinAlgError:
                mahal = np.sum(diff ** 2, axis=1) / (np.trace(cov) / self._n_features + 1e-6)

            # Student-t robustness weights
            weights = (self.df + self._n_features) / (self.df + mahal)
            weighted_gamma = gamma[:, i] * weights

            # Update covariance
            if self.covariance_type == "full":
                weighted_diff = diff * np.sqrt(weighted_gamma)[:, np.newaxis]
                self.covars_[i] = (weighted_diff.T @ weighted_diff) / gamma_sum
                # Add regularization
                self.covars_[i] += np.eye(self._n_features) * 1e-6
            elif self.covariance_type == "diag":
                self.covars_[i] = (weighted_gamma[:, np.newaxis] * diff ** 2).sum(axis=0) / gamma_sum
                self.covars_[i] = np.clip(self.covars_[i], 1e-6, None)
            else:  # spherical
                self.covars_[i] = (weighted_gamma * (diff ** 2).sum(axis=1)).sum() / (gamma_sum * self._n_features)
                self.covars_[i] = max(self.covars_[i], 1e-6)

    def fit(self, X: np.ndarray) -> "StudentTHMM":
        """
        Fit the model using the EM algorithm.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
            Training data.

        Returns
        -------
        self : StudentTHMM
            Fitted model.
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        self._init_params(X)

        prev_log_likelihood = -np.inf
        for iteration in range(self.n_iter):
            # E-step
            gamma, xi, log_likelihood = self._e_step(X)

            # M-step
            self._m_step(X, gamma, xi)

            # Check convergence
            if abs(log_likelihood - prev_log_likelihood) < self.tol:
                break
            prev_log_likelihood = log_likelihood

        self._is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict the most likely state sequence using Viterbi algorithm.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
            Observations.

        Returns
        -------
        states : np.ndarray of shape (n_samples,)
            Predicted state sequence.
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        log_prob = self._compute_log_likelihood(X)
        n_samples = X.shape[0]

        # Viterbi algorithm
        log_delta = np.zeros((n_samples, self.n_components))
        psi = np.zeros((n_samples, self.n_components), dtype=int)

        log_delta[0] = np.log(self.startprob_ + 1e-10) + log_prob[0]

        log_transmat = np.log(self.transmat_ + 1e-10)
        for t in range(1, n_samples):
            for j in range(self.n_components):
                candidates = log_delta[t - 1] + log_transmat[:, j]
                psi[t, j] = np.argmax(candidates)
                log_delta[t, j] = candidates[psi[t, j]] + log_prob[t, j]

        # Backtrack
        states = np.zeros(n_samples, dtype=int)
        states[-1] = np.argmax(log_delta[-1])

        for t in range(n_samples - 2, -1, -1):
            states[t] = psi[t + 1, states[t + 1]]

        return states

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Compute posterior state probabilities.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
            Observations.

        Returns
        -------
        proba : np.ndarray of shape (n_samples, n_components)
            Posterior probabilities.
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        log_prob = self._compute_log_likelihood(X)
        log_alpha, _ = self._forward(log_prob)
        log_beta = self._backward(log_prob)

        log_gamma = log_alpha + log_beta
        log_gamma -= logsumexp(log_gamma, axis=1, keepdims=True)

        return np.exp(log_gamma)

    def score(self, X: np.ndarray) -> float:
        """
        Compute the log-likelihood of the data.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
            Observations.

        Returns
        -------
        log_likelihood : float
            Log-likelihood of the data.
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        log_prob = self._compute_log_likelihood(X)
        _, log_likelihood = self._forward(log_prob)

        return log_likelihood
