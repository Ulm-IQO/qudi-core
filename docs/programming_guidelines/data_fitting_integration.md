---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Fitting
Qudi provides drop-in objects that can be used in logic and corresponding GUI modules to facilitate 
implementation of data fitting and fit constraint configuration.

## Adding custom fit models

Users can provide custom fit models that loaded at runtime. To this end, you need to provide the models as ```.py``` files in one of the following locations:

      qudi-core/src/qudi/util/fit_models
      qudi-iqo-modules/src/qudi/util/fit_models
      <custom-modules>/src/qudi/util/fit_models

Each fit model is implemented as a class that inherits from FitModelBase and needs to have the following minimal functions:

```python

    from qudi.util.fit_models.model import FitModelBase, estimator

    class CustomLinearFit(FitModelBase):
        """
        """
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_param_hint('slope', value=1., min=-np.inf, max=np.inf)
    
        @staticmethod
        def _model_function(x, slope):
            return slope* x

        # optional, make a good initial guess for the optimize
        @estimator('default')  # provide different estimators specified by name string
        def estimate(self, data, x):
            y_span = max(data) - min(data)
            x_span = max(x) - min(x)
            estimate = self.make_params()
            estimate['slope'] = y_span/x_span

            return estimate
```

#Todo: More Documentation
---

[index](../index.md)
