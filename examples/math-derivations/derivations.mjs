// Original annotated derivations; shared with the online morphology viewer.
export const derivations = [
  {
    "id": "derive-quadratic",
    "title": "Quadratic formula by completing the square",
    "group": "Algebra",
    "assumptions": "Real a,b,c; a ≠ 0. Real roots require b² − 4ac ≥ 0.",
    "steps": [
      {
        "math": "ax^2+bx+c=0",
        "note": "Start from the general quadratic.",
        "geometry": null
      },
      {
        "math": "x^2+\\frac{b}{a}x=-\\frac{c}{a}",
        "note": "Divide by nonzero a.",
        "geometry": null
      },
      {
        "math": "x^2+\\frac{b}{a}x+\\frac{b^2}{4a^2}=\\frac{b^2-4ac}{4a^2}",
        "note": "Complete the square on both sides.",
        "geometry": null
      },
      {
        "math": "\\left(x+\\frac{b}{2a}\\right)^2=\\frac{b^2-4ac}{4a^2}",
        "note": "Recognize the square.",
        "geometry": null
      },
      {
        "math": "2ax+b=\\pm\\sqrt{b^2-4ac}",
        "note": "The ± sign includes both branches, also when a is negative.",
        "geometry": null
      },
      {
        "math": "x=\\frac{-b\\pm\\sqrt{b^2-4ac}}{2a}",
        "note": "Isolate x; the two roots coincide when the discriminant is zero.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-weighted-series",
    "title": "Differentiate a geometric series twice",
    "group": "Series",
    "assumptions": "|r| < 1; power series may be differentiated inside their convergence disk.",
    "steps": [
      {
        "math": "S(r)=\\sum_{n=0}^{\\infty}r^n=\\frac{1}{1-r}",
        "note": "Start with the geometric series.",
        "geometry": null
      },
      {
        "math": "S^{\\prime}(r)=\\sum_{n=1}^{\\infty}nr^{n-1}=\\frac{1}{(1-r)^2}",
        "note": "Differentiate term by term.",
        "geometry": null
      },
      {
        "math": "rS^{\\prime}(r)=\\sum_{n=1}^{\\infty}nr^n=\\frac{r}{(1-r)^2}",
        "note": "Multiply by r.",
        "geometry": null
      },
      {
        "math": "\\frac{d}{dr}\\left(\\frac{r}{(1-r)^2}\\right)=\\frac{1+r}{(1-r)^3}",
        "note": "Differentiate the weighted series.",
        "geometry": null
      },
      {
        "math": "\\sum_{n=1}^{\\infty}n^2r^n=\\frac{r(1+r)}{(1-r)^3}",
        "note": "Multiply by r again.",
        "geometry": null
      },
      {
        "math": "\\sum_{n=1}^{\\infty}\\frac{n^2}{2^n}=6",
        "note": "Evaluate at r = 1/2.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-least-squares",
    "title": "Normal equations from a quadratic objective",
    "group": "Linear algebra",
    "assumptions": "Real A has full column rank; b is a real vector.",
    "steps": [
      {
        "math": "J(x)=\\frac{1}{2}(Ax-b)^T(Ax-b)",
        "note": "Minimize squared residual length.",
        "geometry": null
      },
      {
        "math": "J(x)=\\frac{1}{2}x^TA^TAx-x^TA^Tb+\\frac{1}{2}b^Tb",
        "note": "Expand the quadratic.",
        "geometry": null
      },
      {
        "math": "\\nabla J(x)=A^TAx-A^Tb",
        "note": "Differentiate with respect to x.",
        "geometry": null
      },
      {
        "math": "A^TA\\hat{x}=A^Tb",
        "note": "Stationarity gives the normal equations.",
        "geometry": null
      },
      {
        "math": "\\nabla^2J=A^TA",
        "note": "Full column rank makes this Hessian positive definite.",
        "geometry": null
      },
      {
        "math": "\\hat{x}=(A^TA)^{-1}A^Tb",
        "note": "Unique minimizer; numerically, QR or SVD avoids forming this inverse.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-ridge",
    "title": "Ridge regression in singular-value coordinates",
    "group": "Linear algebra",
    "assumptions": "λ > 0; A = UΣVᵀ is a thin SVD.",
    "steps": [
      {
        "math": "J(x)=\\|Ax-b\\|^2+\\lambda\\|x\\|^2",
        "note": "Penalize coefficient size.",
        "geometry": null
      },
      {
        "math": "\\nabla J=2A^T(Ax-b)+2\\lambda x",
        "note": "Differentiate both terms.",
        "geometry": null
      },
      {
        "math": "(A^TA+\\lambda I)x=A^Tb",
        "note": "The shifted matrix is invertible.",
        "geometry": null
      },
      {
        "math": "A=U\\Sigma V^T",
        "note": "Introduce the singular-value decomposition.",
        "geometry": null
      },
      {
        "math": "\\hat{x}=V(\\Sigma^T\\Sigma+\\lambda I)^{-1}\\Sigma^TU^Tb",
        "note": "Resolve the solution on the row-space singular vectors; the orthogonal component is zero.",
        "geometry": null
      },
      {
        "math": "\\hat{x}=\\sum_i\\frac{\\sigma_i}{\\sigma_i^2+\\lambda}v_i u_i^Tb",
        "note": "Each singular direction receives a regularized weight.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-schur",
    "title": "Block elimination and the Schur complement",
    "group": "Linear algebra",
    "assumptions": "A and S = D − CA⁻¹B are invertible; block sizes are compatible.",
    "steps": [
      {
        "math": "Ax+By=f,\\quad Cx+Dy=g",
        "note": "Write the block system.",
        "geometry": null
      },
      {
        "math": "x=A^{-1}(f-By)",
        "note": "Eliminate x using the first block equation.",
        "geometry": null
      },
      {
        "math": "CA^{-1}(f-By)+Dy=g",
        "note": "Substitute into the second equation.",
        "geometry": null
      },
      {
        "math": "(D-CA^{-1}B)y=g-CA^{-1}f",
        "note": "Collect terms multiplying y.",
        "geometry": null
      },
      {
        "math": "S=D-CA^{-1}B,\\quad y=S^{-1}(g-CA^{-1}f)",
        "note": "Solve the Schur-complement system.",
        "geometry": null
      },
      {
        "math": "x=A^{-1}f-A^{-1}BS^{-1}(g-CA^{-1}f)",
        "note": "Back-substitute to recover x.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-eigenvalues",
    "title": "Eigenvalues of a symmetric 2×2 matrix",
    "group": "Linear algebra",
    "assumptions": "a,b,d are real; the symmetric matrix has real eigenvalues.",
    "steps": [
      {
        "math": "A=\\begin{pmatrix}a&b\\\\b&d\\end{pmatrix}",
        "note": "Start with a real symmetric matrix.",
        "geometry": null
      },
      {
        "math": "\\det(A-\\lambda I)=(a-\\lambda)(d-\\lambda)-b^2",
        "note": "Expand the characteristic determinant.",
        "geometry": null
      },
      {
        "math": "\\lambda^2-(a+d)\\lambda+ad-b^2=0",
        "note": "Collect powers of λ.",
        "geometry": null
      },
      {
        "math": "\\lambda_{\\pm}=\\frac{a+d\\pm\\sqrt{(a+d)^2-4(ad-b^2)}}{2}",
        "note": "Apply the quadratic formula.",
        "geometry": null
      },
      {
        "math": "\\lambda_{\\pm}=\\frac{a+d}{2}\\pm\\sqrt{\\left(\\frac{a-d}{2}\\right)^2+b^2}",
        "note": "Simplify the discriminant.",
        "geometry": null
      },
      {
        "math": "\\lambda_++\\lambda_-=a+d,\\quad\\lambda_+\\lambda_-=ad-b^2",
        "note": "Check trace and determinant invariants.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-gaussian-integral",
    "title": "Gaussian integral through polar coordinates",
    "group": "Calculus",
    "assumptions": "Integrands are nonnegative; Tonelli permits the product integral.",
    "steps": [
      {
        "math": "I=\\int_{-\\infty}^{\\infty}e^{-x^2}\\,dx",
        "note": "Define the positive integral.",
        "geometry": null
      },
      {
        "math": "I^2=\\int_{-\\infty}^{\\infty}\\int_{-\\infty}^{\\infty}e^{-x^2-y^2}\\,dx\\,dy",
        "note": "Square it as an integral over the plane.",
        "geometry": null
      },
      {
        "math": "x=r\\cos\\theta,\\quad y=r\\sin\\theta",
        "note": "Change to polar coordinates.",
        "geometry": null
      },
      {
        "math": "dx\\,dy=r\\,dr\\,d\\theta",
        "note": "Include the Jacobian.",
        "geometry": null
      },
      {
        "math": "I^2=\\int_0^{2\\pi}\\int_0^{\\infty}e^{-r^2}r\\,dr\\,d\\theta",
        "note": "The radial and angular factors separate.",
        "geometry": null
      },
      {
        "math": "I^2=2\\pi\\left[-\\frac{1}{2}e^{-r^2}\\right]_0^{\\infty}=\\pi",
        "note": "Evaluate the radial integral.",
        "geometry": null
      },
      {
        "math": "I=\\sqrt{\\pi}",
        "note": "Take the positive root.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-gamma-half",
    "title": "Gamma recurrence and Γ(1/2)",
    "group": "Special functions",
    "assumptions": "s > 0; boundary terms vanish in the integration by parts.",
    "steps": [
      {
        "math": "\\Gamma(s)=\\int_0^{\\infty}t^{s-1}e^{-t}\\,dt",
        "note": "Define the gamma function.",
        "geometry": null
      },
      {
        "math": "\\Gamma(s+1)=\\left[-t^se^{-t}\\right]_0^{\\infty}+s\\int_0^{\\infty}t^{s-1}e^{-t}\\,dt",
        "note": "Integrate by parts.",
        "geometry": null
      },
      {
        "math": "\\Gamma(s+1)=s\\Gamma(s)",
        "note": "Obtain the recurrence.",
        "geometry": null
      },
      {
        "math": "\\Gamma\\left(\\frac{1}{2}\\right)=2\\int_0^{\\infty}e^{-u^2}\\,du",
        "note": "Substitute t = u².",
        "geometry": null
      },
      {
        "math": "\\Gamma\\left(\\frac{1}{2}\\right)=\\sqrt{\\pi}",
        "note": "Use the Gaussian integral.",
        "geometry": null
      },
      {
        "math": "\\Gamma\\left(\\frac{5}{2}\\right)=\\frac{3}{2}\\frac{1}{2}\\sqrt{\\pi}=\\frac{3\\sqrt{\\pi}}{4}",
        "note": "Apply the recurrence twice.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-beta-gamma",
    "title": "Beta–gamma identity via a Jacobian",
    "group": "Special functions",
    "assumptions": "p,q > 0; all integrals converge.",
    "steps": [
      {
        "math": "\\Gamma(p)\\Gamma(q)=\\int_0^{\\infty}\\int_0^{\\infty}x^{p-1}y^{q-1}e^{-x-y}\\,dx\\,dy",
        "note": "Express the product as a double integral.",
        "geometry": null
      },
      {
        "math": "x=ru,\\quad y=r(1-u)",
        "note": "Use r > 0 and 0 < u < 1.",
        "geometry": null
      },
      {
        "math": "\\left|\\frac{\\partial(x,y)}{\\partial(r,u)}\\right|=r",
        "note": "Compute the absolute Jacobian.",
        "geometry": null
      },
      {
        "math": "\\Gamma(p)\\Gamma(q)=\\int_0^{\\infty}r^{p+q-1}e^{-r}\\,dr\\int_0^1u^{p-1}(1-u)^{q-1}\\,du",
        "note": "Separate the transformed variables.",
        "geometry": null
      },
      {
        "math": "\\Gamma(p)\\Gamma(q)=\\Gamma(p+q)B(p,q)",
        "note": "Recognize the two special functions.",
        "geometry": null
      },
      {
        "math": "B(p,q)=\\frac{\\Gamma(p)\\Gamma(q)}{\\Gamma(p+q)}",
        "note": "Divide by the positive gamma factor.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-parameter-integral",
    "title": "An integral evaluated by differentiating a parameter",
    "group": "Calculus",
    "assumptions": "a ≥ 0; differentiation under the integral is justified on bounded parameter intervals.",
    "steps": [
      {
        "math": "F(a)=\\int_0^1\\frac{x^a-1}{\\ln x}\\,dx",
        "note": "The quotient has its removable endpoint value at x = 1.",
        "geometry": null
      },
      {
        "math": "F^{\\prime}(a)=\\int_0^1x^a\\,dx",
        "note": "Differentiate with respect to a.",
        "geometry": null
      },
      {
        "math": "F^{\\prime}(a)=\\frac{1}{a+1}",
        "note": "Evaluate the power integral.",
        "geometry": null
      },
      {
        "math": "F(a)=\\ln(a+1)+C",
        "note": "Integrate in the parameter.",
        "geometry": null
      },
      {
        "math": "F(0)=0,\\quad C=0",
        "note": "Use the initial parameter value.",
        "geometry": null
      },
      {
        "math": "\\int_0^1\\frac{x^a-1}{\\ln x}\\,dx=\\ln(a+1)",
        "note": "Recover the original integral.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-integrating-factor",
    "title": "A linear ODE with a nonconstant coefficient",
    "group": "Differential equations",
    "assumptions": "x is real; y(0) = y₀.",
    "steps": [
      {
        "math": "y^{\\prime}+2xy=x",
        "note": "Start with the linear ODE.",
        "geometry": null
      },
      {
        "math": "\\mu(x)=e^{\\int2x\\,dx}=e^{x^2}",
        "note": "Construct the integrating factor.",
        "geometry": null
      },
      {
        "math": "e^{x^2}y^{\\prime}+2xe^{x^2}y=xe^{x^2}",
        "note": "Multiply the equation.",
        "geometry": null
      },
      {
        "math": "\\frac{d}{dx}(e^{x^2}y)=xe^{x^2}",
        "note": "Recognize a product derivative.",
        "geometry": null
      },
      {
        "math": "e^{x^2}y=\\frac{1}{2}e^{x^2}+C",
        "note": "Integrate.",
        "geometry": null
      },
      {
        "math": "y(x)=\\frac{1}{2}+\\left(y_0-\\frac{1}{2}\\right)e^{-x^2}",
        "note": "Apply the initial condition.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-logistic",
    "title": "Logistic growth by separation of variables",
    "group": "Differential equations",
    "assumptions": "r,K > 0 and 0 < P₀ < K; equilibrium solutions P = 0 and P = K are separate.",
    "steps": [
      {
        "math": "P^{\\prime}=rP\\left(1-\\frac{P}{K}\\right)",
        "note": "Start with logistic growth.",
        "geometry": null
      },
      {
        "math": "\\frac{K\\,dP}{P(K-P)}=r\\,dt",
        "note": "Separate variables away from the equilibria.",
        "geometry": null
      },
      {
        "math": "\\left(\\frac{1}{P}+\\frac{1}{K-P}\\right)dP=r\\,dt",
        "note": "Decompose into partial fractions.",
        "geometry": null
      },
      {
        "math": "\\ln P-\\ln(K-P)=rt+C",
        "note": "Integrate on 0 < P < K.",
        "geometry": null
      },
      {
        "math": "\\frac{P}{K-P}=Ae^{rt}",
        "note": "Exponentiate.",
        "geometry": null
      },
      {
        "math": "P(t)=\\frac{K}{1+\\left(\\frac{K-P_0}{P_0}\\right)e^{-rt}}",
        "note": "Solve for P and impose P(0) = P₀.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-damped-oscillator",
    "title": "Underdamped motion from the characteristic roots",
    "group": "Differential equations",
    "assumptions": "ω₀ > γ ≥ 0; y(0) = y₀ and y′(0) = v₀.",
    "steps": [
      {
        "math": "y^{\\prime\\prime}+2\\gamma y^{\\prime}+\\omega_0^2y=0",
        "note": "A damped oscillator.",
        "geometry": null
      },
      {
        "math": "\\lambda^2+2\\gamma\\lambda+\\omega_0^2=0",
        "note": "Use an exponential trial solution.",
        "geometry": null
      },
      {
        "math": "\\lambda=-\\gamma\\pm i\\sqrt{\\omega_0^2-\\gamma^2}",
        "note": "The underdamped roots are complex conjugates.",
        "geometry": null
      },
      {
        "math": "\\omega=\\sqrt{\\omega_0^2-\\gamma^2}",
        "note": "Define the damped frequency.",
        "geometry": null
      },
      {
        "math": "y(t)=e^{-\\gamma t}(A\\cos\\omega t+B\\sin\\omega t)",
        "note": "Combine into a real solution.",
        "geometry": null
      },
      {
        "math": "y(t)=e^{-\\gamma t}\\left(y_0\\cos\\omega t+\\frac{v_0+\\gamma y_0}{\\omega}\\sin\\omega t\\right)",
        "note": "Impose both initial conditions.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-euler-lagrange",
    "title": "Euler–Lagrange equation from the first variation",
    "group": "Mechanics",
    "assumptions": "L is smooth; variations η vanish at endpoints; paths are sufficiently differentiable.",
    "steps": [
      {
        "math": "S[q]=\\int_a^b L(q,\\dot q,t)\\,dt",
        "note": "Define the action.",
        "geometry": null
      },
      {
        "math": "q_{\\varepsilon}=q+\\varepsilon\\eta,\\quad\\eta(a)=\\eta(b)=0",
        "note": "Vary the path with fixed endpoints.",
        "geometry": null
      },
      {
        "math": "\\delta S=\\int_a^b\\left(\\frac{\\partial L}{\\partial q}\\eta+\\frac{\\partial L}{\\partial\\dot q}\\dot\\eta\\right)dt",
        "note": "Differentiate with respect to ε at zero.",
        "geometry": null
      },
      {
        "math": "\\delta S=\\left[\\frac{\\partial L}{\\partial\\dot q}\\eta\\right]_a^b+\\int_a^b\\left(\\frac{\\partial L}{\\partial q}-\\frac{d}{dt}\\frac{\\partial L}{\\partial\\dot q}\\right)\\eta\\,dt",
        "note": "Integrate the velocity term by parts.",
        "geometry": null
      },
      {
        "math": "\\int_a^b\\left(\\frac{\\partial L}{\\partial q}-\\frac{d}{dt}\\frac{\\partial L}{\\partial\\dot q}\\right)\\eta\\,dt=0",
        "note": "Endpoint variations eliminate the boundary term.",
        "geometry": null
      },
      {
        "math": "\\frac{d}{dt}\\frac{\\partial L}{\\partial\\dot q}-\\frac{\\partial L}{\\partial q}=0",
        "note": "Apply the fundamental lemma of the calculus of variations.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-hamilton",
    "title": "Hamilton’s equations from a Legendre transform",
    "group": "Mechanics",
    "assumptions": "One generalized coordinate; the velocity-to-momentum map is locally invertible.",
    "steps": [
      {
        "math": "p=\\frac{\\partial L}{\\partial\\dot q},\\quad H(q,p,t)=p\\dot q-L",
        "note": "Define momentum and the Hamiltonian.",
        "geometry": null
      },
      {
        "math": "dH=\\dot q\\,dp+p\\,d\\dot q-L_q\\,dq-L_{\\dot q}\\,d\\dot q-L_t\\,dt",
        "note": "Take the total differential.",
        "geometry": null
      },
      {
        "math": "dH=\\dot q\\,dp-L_q\\,dq-L_t\\,dt",
        "note": "Cancel the velocity differentials using p = L velocity derivative.",
        "geometry": null
      },
      {
        "math": "\\dot p=L_q",
        "note": "Use the Euler–Lagrange equation.",
        "geometry": null
      },
      {
        "math": "dH=\\dot q\\,dp-\\dot p\\,dq-L_t\\,dt",
        "note": "Substitute the momentum derivative.",
        "geometry": null
      },
      {
        "math": "\\dot q=\\frac{\\partial H}{\\partial p},\\quad\\dot p=-\\frac{\\partial H}{\\partial q},\\quad H_t=-L_t",
        "note": "Compare coefficients of independent differentials.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-heat-equation",
    "title": "Heat equation: separation and sine modes",
    "group": "Partial differential equations",
    "assumptions": "κ,L > 0; zero Dirichlet boundaries on [0,L]; initial data f is square integrable.",
    "steps": [
      {
        "math": "u_t=\\kappa u_{xx},\\quad u(0,t)=u(L,t)=0",
        "note": "State the equation and boundaries.",
        "geometry": null
      },
      {
        "math": "u(x,t)=X(x)T(t)",
        "note": "Seek a nonzero separated mode.",
        "geometry": null
      },
      {
        "math": "\\frac{T^{\\prime}}{\\kappa T}=\\frac{X^{\\prime\\prime}}{X}=-\\lambda",
        "note": "Separate the independent variables where the factors are nonzero.",
        "geometry": null
      },
      {
        "math": "X^{\\prime\\prime}+\\lambda X=0,\\quad T^{\\prime}+\\kappa\\lambda T=0",
        "note": "Obtain the spatial and temporal ODEs.",
        "geometry": null
      },
      {
        "math": "\\lambda_n=\\left(\\frac{n\\pi}{L}\\right)^2,\\quad X_n=\\sin\\frac{n\\pi x}{L}",
        "note": "Boundary conditions select n = 1,2,… .",
        "geometry": null
      },
      {
        "math": "u(x,t)=\\sum_{n=1}^{\\infty}b_n e^{-\\kappa(n\\pi/L)^2t}\\sin\\frac{n\\pi x}{L}",
        "note": "Superpose the decaying modes.",
        "geometry": null
      },
      {
        "math": "b_n=\\frac{2}{L}\\int_0^L f(x)\\sin\\frac{n\\pi x}{L}\\,dx",
        "note": "Project the initial data onto the sine basis; the initial limit is in L².",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-fourier-gaussian",
    "title": "Fourier transform of a Gaussian via an ODE",
    "group": "Fourier analysis",
    "assumptions": "a > 0; transform convention F(k) = ∫ f(x)e⁻ⁱᵏˣ dx.",
    "steps": [
      {
        "math": "F(k)=\\int_{-\\infty}^{\\infty}e^{-ax^2}e^{-ikx}\\,dx",
        "note": "Define the transform.",
        "geometry": null
      },
      {
        "math": "F^{\\prime}(k)=-i\\int_{-\\infty}^{\\infty}xe^{-ax^2}e^{-ikx}\\,dx",
        "note": "Differentiate under the integral.",
        "geometry": null
      },
      {
        "math": "xe^{-ax^2}=-\\frac{1}{2a}\\frac{d}{dx}e^{-ax^2}",
        "note": "Rewrite the moment as a derivative.",
        "geometry": null
      },
      {
        "math": "F^{\\prime}(k)=-\\frac{k}{2a}F(k)",
        "note": "Integrate by parts; the Gaussian boundary term vanishes.",
        "geometry": null
      },
      {
        "math": "F(k)=F(0)e^{-k^2/(4a)}",
        "note": "Solve the first-order ODE.",
        "geometry": null
      },
      {
        "math": "F(k)=\\sqrt{\\frac{\\pi}{a}}e^{-k^2/(4a)}",
        "note": "Determine the constant from the Gaussian integral.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-fourier-sawtooth",
    "title": "Fourier sine series of a sawtooth",
    "group": "Fourier analysis",
    "assumptions": "Use the 2π-periodic extension of f(x)=x on (−π,π). At jumps the series takes the midpoint value 0.",
    "steps": [
      {
        "math": "f(x)=x,\\quad -\\pi<x<\\pi",
        "note": "The function is odd, so only sine coefficients remain.",
        "geometry": null
      },
      {
        "math": "b_n=\\frac{2}{\\pi}\\int_0^{\\pi}x\\sin(nx)\\,dx",
        "note": "Use odd symmetry.",
        "geometry": null
      },
      {
        "math": "b_n=\\frac{2}{\\pi}\\left[-\\frac{x\\cos(nx)}{n}+\\frac{\\sin(nx)}{n^2}\\right]_0^{\\pi}",
        "note": "Integrate by parts.",
        "geometry": null
      },
      {
        "math": "b_n=\\frac{2(-1)^{n+1}}{n}",
        "note": "Evaluate the endpoint values.",
        "geometry": null
      },
      {
        "math": "x=2\\sum_{n=1}^{\\infty}\\frac{(-1)^{n+1}}{n}\\sin(nx)",
        "note": "The series equals x inside the open interval.",
        "geometry": null
      },
      {
        "math": "\\frac{\\pi}{4}=1-\\frac{1}{3}+\\frac{1}{5}-\\frac{1}{7}+\\cdots",
        "note": "Evaluate at x = π/2.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-normal-mle",
    "title": "Joint normal mean and variance MLE",
    "group": "Probability",
    "assumptions": "Independent normal observations; n ≥ 2 and not all observations coincide; v = σ² > 0.",
    "steps": [
      {
        "math": "L(\\mu,v)=(2\\pi v)^{-n/2}e^{-\\sum_i(x_i-\\mu)^2/(2v)}",
        "note": "Write the joint likelihood.",
        "geometry": null
      },
      {
        "math": "\\ell(\\mu,v)=-\\frac{n}{2}\\ln(2\\pi v)-\\frac{1}{2v}\\sum_i(x_i-\\mu)^2",
        "note": "Take logarithms.",
        "geometry": null
      },
      {
        "math": "\\frac{\\partial\\ell}{\\partial\\mu}=\\frac{1}{v}\\sum_i(x_i-\\mu)=0",
        "note": "Set the mean score to zero.",
        "geometry": null
      },
      {
        "math": "\\hat\\mu=\\bar x=\\frac{1}{n}\\sum_i x_i",
        "note": "Recover the sample mean.",
        "geometry": null
      },
      {
        "math": "\\frac{\\partial\\ell}{\\partial v}=-\\frac{n}{2v}+\\frac{\\sum_i(x_i-\\bar x)^2}{2v^2}=0",
        "note": "Optimize the profile likelihood over positive variance.",
        "geometry": null
      },
      {
        "math": "\\hat v=\\frac{1}{n}\\sum_i(x_i-\\bar x)^2",
        "note": "This is the MLE; its denominator is n, not the unbiased estimator’s n−1.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-normal-posterior",
    "title": "Normal–normal Bayesian posterior",
    "group": "Probability",
    "assumptions": "Independent xᵢ conditional on μ; known σ² > 0; prior μ ~ N(m₀,s₀²), s₀² > 0.",
    "steps": [
      {
        "math": "p(\\mu\\,|\\, x)=C e^{-(\\mu-m_0)^2/(2s_0^2)}e^{-\\sum_i(x_i-\\mu)^2/(2\\sigma^2)}",
        "note": "Multiply prior and likelihood; constants independent of μ are omitted.",
        "geometry": null
      },
      {
        "math": "\\tau=\\frac{1}{s_0^2}+\\frac{n}{\\sigma^2},\\quad h=\\frac{m_0}{s_0^2}+\\frac{n\\bar x}{\\sigma^2}",
        "note": "Collect posterior precision and linear coefficient.",
        "geometry": null
      },
      {
        "math": "\\ln p(\\mu\\,|\\, x)=-\\frac{1}{2}(\\tau\\mu^2-2h\\mu)+C",
        "note": "Expand and collect powers of μ.",
        "geometry": null
      },
      {
        "math": "\\tau\\mu^2-2h\\mu=\\tau\\left(\\mu-\\frac{h}{\\tau}\\right)^2-\\frac{h^2}{\\tau}",
        "note": "Complete the square.",
        "geometry": null
      },
      {
        "math": "m_n=\\frac{h}{\\tau},\\quad s_n^2=\\frac{1}{\\tau}",
        "note": "Identify posterior mean and variance.",
        "geometry": null
      },
      {
        "math": "p(\\mu\\,|\\, x)=\\frac{1}{\\sqrt{2\\pi s_n^2}}e^{-(\\mu-m_n)^2/(2s_n^2)}",
        "note": "Normalize the Gaussian density.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-poisson-limit",
    "title": "Poisson law as a binomial limit",
    "group": "Probability",
    "assumptions": "Fixed integer k ≥ 0 and λ > 0; take n → ∞ with n ≥ k and n > λ.",
    "steps": [
      {
        "math": "P_n(k)=\\binom{n}{k}\\left(\\frac{\\lambda}{n}\\right)^k\\left(1-\\frac{\\lambda}{n}\\right)^{n-k}",
        "note": "Start with a binomial probability.",
        "geometry": null
      },
      {
        "math": "\\binom{n}{k}\\left(\\frac{\\lambda}{n}\\right)^k=\\frac{\\lambda^k}{\\Gamma(k+1)}\\prod_{j=0}^{k-1}\\left(1-\\frac{j}{n}\\right)",
        "note": "Separate the finite product; for k = 0 it is empty and equals one.",
        "geometry": null
      },
      {
        "math": "\\prod_{j=0}^{k-1}\\left(1-\\frac{j}{n}\\right)\\to1",
        "note": "Every factor tends to one for fixed k.",
        "geometry": null
      },
      {
        "math": "n\\ln\\left(1-\\frac{\\lambda}{n}\\right)\\to-\\lambda",
        "note": "Use the first-order logarithm expansion.",
        "geometry": null
      },
      {
        "math": "\\left(1-\\frac{\\lambda}{n}\\right)^{n-k}\\to e^{-\\lambda}",
        "note": "The fixed −k correction tends to one.",
        "geometry": null
      },
      {
        "math": "P_n(k)\\to e^{-\\lambda}\\frac{\\lambda^k}{\\Gamma(k+1)}",
        "note": "Combine the limits.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-kl",
    "title": "Gibbs’ inequality and KL nonnegativity",
    "group": "Information theory",
    "assumptions": "Finite probability vectors p,q with pᵢ,qᵢ > 0; natural logarithms.",
    "steps": [
      {
        "math": "D(p\\|q)=\\sum_i p_i\\ln\\frac{p_i}{q_i}",
        "note": "Define relative entropy.",
        "geometry": null
      },
      {
        "math": "\\ln z\\leq z-1,\\quad z>0",
        "note": "Use the tangent-line bound for the logarithm.",
        "geometry": null
      },
      {
        "math": "-\\ln\\frac{q_i}{p_i}\\geq1-\\frac{q_i}{p_i}",
        "note": "Apply the bound to qᵢ/pᵢ.",
        "geometry": null
      },
      {
        "math": "p_i\\ln\\frac{p_i}{q_i}\\geq p_i-q_i",
        "note": "Multiply by positive pᵢ.",
        "geometry": null
      },
      {
        "math": "D(p\\|q)\\geq\\sum_i p_i-\\sum_i q_i=0",
        "note": "Sum and use normalization.",
        "geometry": null
      },
      {
        "math": "D(p\\|q)=0\\quad\\Longleftrightarrow\\quad p=q",
        "note": "Equality requires every ratio to equal one.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-max-entropy",
    "title": "Maximum entropy with a fixed mean energy",
    "group": "Information theory",
    "assumptions": "Finite states with energies Eᵢ; prescribed mean lies strictly between distinct extreme energies.",
    "steps": [
      {
        "math": "H(p)=-\\sum_i p_i\\ln p_i",
        "note": "Maximize entropy under normalization and a fixed mean energy.",
        "geometry": null
      },
      {
        "math": "\\mathcal L=-\\sum_i p_i\\ln p_i-\\alpha(\\sum_i p_i-1)-\\beta(\\sum_i p_iE_i-U)",
        "note": "Introduce two multipliers.",
        "geometry": null
      },
      {
        "math": "\\frac{\\partial\\mathcal L}{\\partial p_i}=-\\ln p_i-1-\\alpha-\\beta E_i=0",
        "note": "Find the interior stationary distribution.",
        "geometry": null
      },
      {
        "math": "p_i=e^{-1-\\alpha}e^{-\\beta E_i}",
        "note": "Solve the stationarity equation.",
        "geometry": null
      },
      {
        "math": "Z(\\beta)=\\sum_j e^{-\\beta E_j},\\quad p_i=\\frac{e^{-\\beta E_i}}{Z(\\beta)}",
        "note": "Normalization fixes the common factor.",
        "geometry": null
      },
      {
        "math": "U=-\\frac{d}{d\\beta}\\ln Z(\\beta)",
        "note": "Choose β to satisfy the energy constraint; strict concavity guarantees the unique maximizer.",
        "geometry": null
      }
    ]
  },
  {
    "id": "derive-inverse-iteration",
    "title": "Newton–Schulz matrix inverse iteration",
    "group": "Numerical analysis",
    "assumptions": "A is square; a submultiplicative norm satisfies ‖I−AX₀‖ < 1.",
    "steps": [
      {
        "math": "X_{k+1}=X_k(2I-AX_k)",
        "note": "Define the inverse iteration.",
        "geometry": null
      },
      {
        "math": "E_k=I-AX_k",
        "note": "Track the right residual.",
        "geometry": null
      },
      {
        "math": "AX_{k+1}=AX_k(2I-AX_k)",
        "note": "Multiply the update by A.",
        "geometry": null
      },
      {
        "math": "E_{k+1}=I-(I-E_k)(I+E_k)",
        "note": "Substitute AXₖ = I−Eₖ.",
        "geometry": null
      },
      {
        "math": "E_{k+1}=E_k^2",
        "note": "The matrix residual squares at each step.",
        "geometry": null
      },
      {
        "math": "\\|E_k\\|\\leq\\|E_0\\|^{2^k}\\to0",
        "note": "Submultiplicativity yields quadratic convergence to the inverse.",
        "geometry": null
      }
    ]
  }
];
