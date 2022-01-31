r"""
Base class for polyhedra
"""

# ****************************************************************************
#       Copyright (C) 2008-2012 Marshall Hampton <hamptonio@gmail.com>
#       Copyright (C) 2011-2015 Volker Braun <vbraun.name@gmail.com>
#       Copyright (C) 2012-2018 Frederic Chapoton
#       Copyright (C) 2013      Andrey Novoseltsev
#       Copyright (C) 2014-2017 Moritz Firsching
#       Copyright (C) 2014-2019 Thierry Monteil
#       Copyright (C) 2015      Nathann Cohen
#       Copyright (C) 2015-2017 Jeroen Demeyer
#       Copyright (C) 2015-2017 Vincent Delecroix
#       Copyright (C) 2015-2018 Dima Pasechnik
#       Copyright (C) 2015-2020 Jean-Philippe Labbe <labbe at math.huji.ac.il>
#       Copyright (C) 2015-2021 Matthias Koeppe
#       Copyright (C) 2016-2019 Daniel Krenn
#       Copyright (C) 2017      Marcelo Forets
#       Copyright (C) 2017-2018 Mark Bell
#       Copyright (C) 2019      Julian Ritter
#       Copyright (C) 2019-2020 Laith Rastanawi
#       Copyright (C) 2019-2020 Sophia Elia
#       Copyright (C) 2019-2021 Jonathan Kliem <jonathan.kliem@fu-berlin.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************

from sage.cpython.string import bytes_to_str

from sage.misc.cachefunc import cached_method

from sage.rings.integer_ring import ZZ
from sage.rings.qqbar import AA
from sage.rings.rational_field import QQ
from sage.rings.real_double import RDF
from sage.modules.free_module_element import vector
from sage.modules.vector_space_morphism import linear_transformation
from sage.matrix.constructor import matrix
from sage.geometry.convex_set import AffineHullProjectionData

from .base5 import Polyhedron_base5

#########################################################################
# Notes if you want to implement your own backend:
#
#  * derive from Polyhedron_base
#
#  * you must implement _init_from_Vrepresentation and
#    _init_from_Hrepresentation
#
#  * You might want to override _init_empty_polyhedron
#
#  * You may implement _init_from_Vrepresentation_and_Hrepresentation
#
#  * You can of course also override any other method for which you
#    have a faster implementation.
#########################################################################


#########################################################################
def is_Polyhedron(X):
    """
    Test whether ``X`` is a Polyhedron.

    INPUT:

    - ``X`` -- anything.

    OUTPUT:

    Boolean.

    EXAMPLES::

        sage: p = polytopes.hypercube(2)
        sage: from sage.geometry.polyhedron.base import is_Polyhedron
        sage: is_Polyhedron(p)
        True
        sage: is_Polyhedron(123456)
        False
    """
    return isinstance(X, Polyhedron_base)


#########################################################################
class Polyhedron_base(Polyhedron_base5):
    """
    Base class for Polyhedron objects

    INPUT:

    - ``parent`` -- the parent, an instance of
      :class:`~sage.geometry.polyhedron.parent.Polyhedra`.

    - ``Vrep`` -- a list ``[vertices, rays, lines]`` or ``None``. The
      V-representation of the polyhedron. If ``None``, the polyhedron
      is determined by the H-representation.

    - ``Hrep`` -- a list ``[ieqs, eqns]`` or ``None``. The
      H-representation of the polyhedron. If ``None``, the polyhedron
      is determined by the V-representation.

    - ``Vrep_minimal`` (optional) -- see below

    - ``Hrep_minimal`` (optional) -- see below

    - ``pref_rep`` -- string (default: ``None``);
       one of``Vrep`` or ``Hrep`` to pick this in case the backend
       cannot initialize from complete double description

    - ``mutable`` -- ignored

    If both ``Vrep`` and ``Hrep`` are provided, then
    ``Vrep_minimal`` and ``Hrep_minimal`` must be set to ``True``.

    TESTS::

        sage: p = Polyhedron()
        sage: TestSuite(p).run()

    ::

        sage: p = Polyhedron(vertices=[(1,0), (0,1)], rays=[(1,1)], base_ring=ZZ)
        sage: TestSuite(p).run()

    ::

        sage: p=polytopes.flow_polytope(digraphs.DeBruijn(3,2))                                     # optional - sage.graphs
        sage: TestSuite(p).run()                                                                    # optional - sage.graphs

    ::

        sage: TestSuite(Polyhedron([[]])).run()
        sage: TestSuite(Polyhedron([[0]])).run()
        sage: TestSuite(Polyhedron([[1]])).run()

    ::

        sage: P = polytopes.permutahedron(3) * Polyhedron(rays=[[0,0,1],[0,1,1],[1,2,3]])           # optional - sage.combinat
        sage: TestSuite(P).run()                                                                    # optional - sage.combinat

    ::

        sage: P = polytopes.permutahedron(3)*Polyhedron(rays=[[0,0,1],[0,1,1]], lines=[[1,0,0]])    # optional - sage.combinat
        sage: TestSuite(P).run()                                                                    # optional - sage.combinat

    ::

        sage: M = random_matrix(ZZ, 5, 5, distribution='uniform')
        sage: while True:
        ....:     M = random_matrix(ZZ, 5, 5, distribution='uniform')
        ....:     if M.rank() != 5:
        ....:         break
        ....:
        sage: P = Polyhedron(M)
        sage: TestSuite(P).run()
    """

    def _test_basic_properties(self, tester=None, **options):
        """
        Run some basic tests to see, that some general assertion on polyhedra hold.

        TESTS::

            sage: polytopes.cross_polytope(3)._test_basic_properties()
        """
        from .constructor import Polyhedron

        if tester is None:
            tester = self._tester(**options)

        tester.assertEqual(self.n_vertices() + self.n_rays() + self.n_lines(), self.n_Vrepresentation())
        tester.assertEqual(self.n_inequalities() + self.n_equations(), self.n_Hrepresentation())
        if self.n_vertices():
            # Depending on the backend, this does not hold for the empty polyhedron.
            tester.assertEqual(self.dim() + self.n_equations(), self.ambient_dim())

        tester.assertTrue(all(len(v[::]) == self.ambient_dim() for v in self.Vrep_generator()))
        tester.assertTrue(all(len(h[::]) == self.ambient_dim() + 1 for h in self.Hrep_generator()))

        if self.n_vertices() + self.n_rays() < 40:
            tester.assertEqual(self, Polyhedron(vertices=self.vertices(), rays=self.rays(), lines=self.lines(), ambient_dim=self.ambient_dim()))
        if self.n_inequalities() < 40:
            tester.assertEqual(self, Polyhedron(ieqs=self.inequalities(), eqns=self.equations(), ambient_dim=self.ambient_dim()))

    def plot(self,
             point=None, line=None, polygon=None,  # None means unspecified by the user
             wireframe='blue', fill='green',
             position=None,
             orthonormal=True,  # whether to use orthonormal projections
             **kwds):
        """
        Return a graphical representation.

        INPUT:

        - ``point``, ``line``, ``polygon`` -- Parameters to pass to
          point (0d), line (1d), and polygon (2d) plot commands.
          Allowed values are:

          * A Python dictionary to be passed as keywords to the plot
            commands.

          * A string or triple of numbers: The color. This is
            equivalent to passing the dictionary ``{'color':...}``.

          * ``False``: Switches off the drawing of the corresponding
            graphics object

        - ``wireframe``, ``fill`` -- Similar to ``point``, ``line``,
          and ``polygon``, but ``fill`` is used for the graphics
          objects in the dimension of the polytope (or of dimension 2
          for higher dimensional polytopes) and ``wireframe`` is used
          for all lower-dimensional graphics objects
          (default: 'green' for ``fill`` and 'blue' for ``wireframe``)

        - ``position`` -- positive number; the position to take the projection
          point in Schlegel diagrams.

        - ``orthonormal`` -- Boolean (default: True); whether to use
          orthonormal projections.

        - ``**kwds`` -- optional keyword parameters that are passed to
          all graphics objects.

        OUTPUT:

        A (multipart) graphics object.

        EXAMPLES::

            sage: square = polytopes.hypercube(2)
            sage: point = Polyhedron([[1,1]])
            sage: line = Polyhedron([[1,1],[2,1]])
            sage: cube = polytopes.hypercube(3)
            sage: hypercube = polytopes.hypercube(4)

        By default, the wireframe is rendered in blue and the fill in green::

            sage: square.plot()  # optional - sage.plot
            Graphics object consisting of 6 graphics primitives
            sage: point.plot()  # optional - sage.plot
            Graphics object consisting of 1 graphics primitive
            sage: line.plot()  # optional - sage.plot
            Graphics object consisting of 2 graphics primitives
            sage: cube.plot()  # optional - sage.plot
            Graphics3d Object
            sage: hypercube.plot()  # optional - sage.plot
            Graphics3d Object

        Draw the lines in red and nothing else::

            sage: square.plot(point=False, line='red', polygon=False)  # optional - sage.plot
            Graphics object consisting of 4 graphics primitives
            sage: point.plot(point=False, line='red', polygon=False)  # optional - sage.plot
            Graphics object consisting of 0 graphics primitives
            sage: line.plot(point=False, line='red', polygon=False)  # optional - sage.plot
            Graphics object consisting of 1 graphics primitive
            sage: cube.plot(point=False, line='red', polygon=False)  # optional - sage.plot
            Graphics3d Object
            sage: hypercube.plot(point=False, line='red', polygon=False)  # optional - sage.plot
            Graphics3d Object

        Draw points in red, no lines, and a blue polygon::

            sage: square.plot(point={'color':'red'}, line=False, polygon=(0,0,1))  # optional - sage.plot
            Graphics object consisting of 2 graphics primitives
            sage: point.plot(point={'color':'red'}, line=False, polygon=(0,0,1))  # optional - sage.plot
            Graphics object consisting of 1 graphics primitive
            sage: line.plot(point={'color':'red'}, line=False, polygon=(0,0,1))  # optional - sage.plot
            Graphics object consisting of 1 graphics primitive
            sage: cube.plot(point={'color':'red'}, line=False, polygon=(0,0,1))  # optional - sage.plot
            Graphics3d Object
            sage: hypercube.plot(point={'color':'red'}, line=False, polygon=(0,0,1))  # optional - sage.plot
            Graphics3d Object

        If we instead use the ``fill`` and ``wireframe`` options, the
        coloring depends on the dimension of the object::

            sage: square.plot(fill='green', wireframe='red')  # optional - sage.plot
            Graphics object consisting of 6 graphics primitives
            sage: point.plot(fill='green', wireframe='red')  # optional - sage.plot
            Graphics object consisting of 1 graphics primitive
            sage: line.plot(fill='green', wireframe='red')  # optional - sage.plot
            Graphics object consisting of 2 graphics primitives
            sage: cube.plot(fill='green', wireframe='red')  # optional - sage.plot
            Graphics3d Object
            sage: hypercube.plot(fill='green', wireframe='red')  # optional - sage.plot
            Graphics3d Object

        It is possible to draw polyhedra up to dimension 4, no matter what the
        ambient dimension is::

            sage: hcube = polytopes.hypercube(5)
            sage: facet = hcube.facets()[0].as_polyhedron();facet
            A 4-dimensional polyhedron in ZZ^5 defined as the convex hull of 16 vertices
            sage: facet.plot()  # optional - sage.plot
            Graphics3d Object

        TESTS::

            sage: for p in square.plot():  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            blue Point set defined by 4 point(s)
            blue Line defined by 2 points
            blue Line defined by 2 points
            blue Line defined by 2 points
            blue Line defined by 2 points
            green Polygon defined by 4 points

            sage: for p in line.plot():  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            blue Point set defined by 2 point(s)
            green Line defined by 2 points

            sage: for p in point.plot():  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            green Point set defined by 1 point(s)

        Draw the lines in red and nothing else::

            sage: for p in square.plot(point=False, line='red', polygon=False):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Line defined by 2 points
            red Line defined by 2 points
            red Line defined by 2 points
            red Line defined by 2 points

        Draw vertices in red, no lines, and a blue polygon::

            sage: for p in square.plot(point={'color':'red'}, line=False, polygon=(0,0,1)):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Point set defined by 4 point(s)
            (0, 0, 1) Polygon defined by 4 points

            sage: for p in line.plot(point={'color':'red'}, line=False, polygon=(0,0,1)):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Point set defined by 2 point(s)

            sage: for p in point.plot(point={'color':'red'}, line=False, polygon=(0,0,1)):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Point set defined by 1 point(s)

        Draw in red without wireframe::

            sage: for p in square.plot(wireframe=False, fill="red"):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Polygon defined by 4 points

            sage: for p in line.plot(wireframe=False, fill="red"):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Line defined by 2 points

            sage: for p in point.plot(wireframe=False, fill="red"):  # optional - sage.plot
            ....:     print("{} {}".format(p.options()['rgbcolor'], p))
            red Point set defined by 1 point(s)

        We try to draw the polytope in 2 or 3 dimensions::

            sage: type(Polyhedron(ieqs=[(1,)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(polytopes.hypercube(1).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(polytopes.hypercube(2).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(polytopes.hypercube(3).plot())  # optional - sage.plot
            <class 'sage.plot.plot3d.base.Graphics3dGroup'>

        In 4d a projection to 3d is used::

            sage: type(polytopes.hypercube(4).plot())  # optional - sage.plot
            <class 'sage.plot.plot3d.base.Graphics3dGroup'>
            sage: type(polytopes.hypercube(5).plot())  # optional - sage.plot
            Traceback (most recent call last):
            ...
            NotImplementedError: plotting of 5-dimensional polyhedra not implemented

        If the polyhedron is not full-dimensional, the :meth:`affine_hull_projection` is used if necessary::

            sage: type(Polyhedron([(0,), (1,)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(Polyhedron([(0,0), (1,1)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(Polyhedron([(0,0,0), (1,1,1)]).plot())  # optional - sage.plot
            <class 'sage.plot.plot3d.base.Graphics3dGroup'>
            sage: type(Polyhedron([(0,0,0,0), (1,1,1,1)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(Polyhedron([(0,0,0,0,0), (1,1,1,1,1)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>
            sage: type(Polyhedron([(0,0,0,0), (1,1,1,1), (1,0,0,0)]).plot())  # optional - sage.plot
            <class 'sage.plot.graphics.Graphics'>

        TESTS:

        Check that :trac:`30015` is fixed::

            sage: fcube = polytopes.hypercube(4)
            sage: tfcube = fcube.face_truncation(fcube.faces(0)[0])
            sage: sp = tfcube.schlegel_projection()
            sage: for face in tfcube.faces(2):
            ....:     vertices = face.ambient_Vrepresentation()
            ....:     indices = [sp.coord_index_of(vector(x)) for x in vertices]
            ....:     projected_vertices = [sp.transformed_coords[i] for i in indices]
            ....:     assert Polyhedron(projected_vertices).dim() == 2
        """
        def merge_options(*opts):
            merged = dict()
            for i in range(len(opts)):
                opt = opts[i]
                if opt is None:
                    continue
                elif opt is False:
                    return False
                elif isinstance(opt, (str, list, tuple)):
                    merged['color'] = opt
                else:
                    merged.update(opt)
            return merged

        d = min(self.dim(), 2)
        opts = [wireframe] * d + [fill] + [False] * (2-d)
        # The point/line/polygon options take precedence over wireframe/fill
        opts = [merge_options(opt1, opt2, kwds)
                for opt1, opt2 in zip(opts, [point, line, polygon])]

        def project(polyhedron, ortho):
            if polyhedron.ambient_dim() <= 3:
                return polyhedron.projection()
            elif polyhedron.dim() <= 3:
                if ortho:
                    return polyhedron.affine_hull_projection(orthonormal=True, extend=True).projection()
                else:
                    return polyhedron.affine_hull_projection().projection()
            elif polyhedron.dimension() == 4:
                # For 4d-polyhedron, we can use schlegel projections:
                return polyhedron.schlegel_projection(position=position)
            else:
                return polyhedron.projection()

        projection = project(self, orthonormal)
        try:
            plot_method = projection.plot
        except AttributeError:
            raise NotImplementedError('plotting of {0}-dimensional polyhedra not implemented'
                                          .format(self.ambient_dim()))
        return plot_method(*opts)

    def show(self, **kwds):
        """
        Display graphics immediately

        This method attempts to display the graphics immediately,
        without waiting for the currently running code (if any) to
        return to the command line. Be careful, calling it from within
        a loop will potentially launch a large number of external
        viewer programs.

        INPUT:

        - ``kwds`` -- optional keyword arguments. See :meth:`plot` for
          the description of available options.

        OUTPUT:

        This method does not return anything. Use :meth:`plot` if you
        want to generate a graphics object that can be saved or
        further transformed.

        EXAMPLES::

            sage: square = polytopes.hypercube(2)
            sage: square.show(point='red')         # optional - sage.plot
        """
        self.plot(**kwds).show()

    def tikz(self, view=[0, 0, 1], angle=0, scale=1,
             edge_color='blue!95!black', facet_color='blue!95!black',
             opacity=0.8, vertex_color='green', axis=False):
        r"""
        Return a string ``tikz_pic`` consisting of a tikz picture of ``self``
        according to a projection ``view`` and an angle ``angle``
        obtained via the threejs viewer.

        INPUT:

        - ``view`` - list (default: [0,0,1]) representing the rotation axis (see note below).
        - ``angle`` - integer (default: 0) angle of rotation in degree from 0 to 360 (see note
          below).
        - ``scale`` - integer (default: 1) specifying the scaling of the tikz picture.
        - ``edge_color`` - string (default: 'blue!95!black') representing colors which tikz
          recognize.
        - ``facet_color`` - string (default: 'blue!95!black') representing colors which tikz
          recognize.
        - ``vertex_color`` - string (default: 'green') representing colors which tikz
          recognize.
        - ``opacity`` - real number (default: 0.8) between 0 and 1 giving the opacity of
          the front facets.
        - ``axis`` - Boolean (default: False) draw the axes at the origin or not.

        OUTPUT:

        - LatexExpr -- containing the TikZ picture.

        .. NOTE::

            This is a wrapper of a method of the projection object
            `self.projection()`. See :meth:`~sage.geometry.polyhedron.plot.Projection.tikz`
            for more detail.

            The inputs ``view`` and ``angle`` can be obtained by visualizing it
            using ``.show(aspect_ratio=1)``. This will open an interactive view
            in your default browser, where you can rotate the polytope. Once
            the desired view angle is found, click on the information icon in
            the lower right-hand corner and select *Get Viewpoint*. This will
            copy a string of the form '[x,y,z],angle' to your local clipboard.
            Go back to Sage and type ``Img = P.tikz([x,y,z],angle)``.

            The inputs ``view`` and ``angle`` can also be obtained from the
            viewer Jmol::

                1) Right click on the image
                2) Select ``Console``
                3) Select the tab ``State``
                4) Scroll to the line ``moveto``

            It reads something like::

                moveto 0.0 {x y z angle} Scale

            The ``view`` is then [x,y,z] and ``angle`` is angle.
            The following number is the scale.

            Jmol performs a rotation of ``angle`` degrees along the
            vector [x,y,z] and show the result from the z-axis.


        EXAMPLES::

            sage: co = polytopes.cuboctahedron()
            sage: Img = co.tikz([0,0,1], 0)
            sage: print('\n'.join(Img.splitlines()[:9]))
            \begin{tikzpicture}%
                [x={(1.000000cm, 0.000000cm)},
                y={(0.000000cm, 1.000000cm)},
                z={(0.000000cm, 0.000000cm)},
                scale=1.000000,
                back/.style={loosely dotted, thin},
                edge/.style={color=blue!95!black, thick},
                facet/.style={fill=blue!95!black,fill opacity=0.800000},
                vertex/.style={inner sep=1pt,circle,draw=green!25!black,fill=green!75!black,thick}]
            sage: print('\n'.join(Img.splitlines()[12:21]))
            %% with the command: ._tikz_3d_in_3d and parameters:
            %% view = [0, 0, 1]
            %% angle = 0
            %% scale = 1
            %% edge_color = blue!95!black
            %% facet_color = blue!95!black
            %% opacity = 0.8
            %% vertex_color = green
            %% axis = False
            sage: print('\n'.join(Img.splitlines()[22:26]))
            %% Coordinate of the vertices:
            %%
            \coordinate (-1.00000, -1.00000, 0.00000) at (-1.00000, -1.00000, 0.00000);
            \coordinate (-1.00000, 0.00000, -1.00000) at (-1.00000, 0.00000, -1.00000);
        """
        return self.projection().tikz(view, angle, scale,
                                      edge_color, facet_color,
                                      opacity, vertex_color, axis)

    def _rich_repr_(self, display_manager, **kwds):
        r"""
        Rich Output Magic Method

        See :mod:`sage.repl.rich_output` for details.

        EXAMPLES::

            sage: from sage.repl.rich_output import get_display_manager
            sage: dm = get_display_manager()
            sage: polytopes.hypercube(2)._rich_repr_(dm)
            OutputPlainText container

        The ``supplemental_plot`` preference lets us control whether
        this object is shown as text or picture+text::

            sage: dm.preferences.supplemental_plot
            'never'
            sage: del dm.preferences.supplemental_plot
            sage: polytopes.hypercube(3)
            A 3-dimensional polyhedron in ZZ^3 defined as the convex hull of 8 vertices (use the .plot() method to plot)
            sage: dm.preferences.supplemental_plot = 'never'
        """
        prefs = display_manager.preferences
        is_small = (self.ambient_dim() <= 2)
        can_plot = (prefs.supplemental_plot != 'never')
        plot_graph = can_plot and (prefs.supplemental_plot == 'always' or is_small)
        # Under certain circumstances we display the plot as graphics
        if plot_graph:
            plot_kwds = dict(kwds)
            plot_kwds.setdefault('title', repr(self))
            output = self.plot(**plot_kwds)._rich_repr_(display_manager)
            if output is not None:
                return output
        # create text for non-graphical output
        if can_plot:
            text = '{0} (use the .plot() method to plot)'.format(repr(self))
        else:
            text = repr(self)
        # latex() produces huge tikz environment, override
        tp = display_manager.types
        if (prefs.text == 'latex' and tp.OutputLatex in display_manager.supported_output()):
            return tp.OutputLatex(r'\text{{{0}}}'.format(text))
        return tp.OutputPlainText(text)

    def cdd_Hrepresentation(self):
        r"""
        Write the inequalities/equations data of the polyhedron in
        cdd's H-representation format.

        .. SEEALSO::

            :meth:`write_cdd_Hrepresentation` -- export the polyhedron as a
            H-representation to a file.

        OUTPUT: a string

        EXAMPLES::

            sage: p = polytopes.hypercube(2)
            sage: print(p.cdd_Hrepresentation())
            H-representation
            begin
             4 3 rational
             1 -1 0
             1 0 -1
             1 1 0
             1 0 1
            end
            <BLANKLINE>

            sage: triangle = Polyhedron(vertices=[[1,0], [0,1], [1,1]], base_ring=AA)   # optional - sage.rings.number_field
            sage: triangle.base_ring()                                                  # optional - sage.rings.number_field
            Algebraic Real Field
            sage: triangle.cdd_Hrepresentation()                                        # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            TypeError: the base ring must be ZZ, QQ, or RDF
        """
        from .cdd_file_format import cdd_Hrepresentation
        try:
            cdd_type = self._cdd_type
        except AttributeError:
            if self.base_ring() is ZZ or self.base_ring() is QQ:
                cdd_type = 'rational'
            elif self.base_ring() is RDF:
                cdd_type = 'real'
            else:
                raise TypeError('the base ring must be ZZ, QQ, or RDF')
        return cdd_Hrepresentation(cdd_type,
                                   list(self.inequality_generator()),
                                   list(self.equation_generator()))

    def write_cdd_Hrepresentation(self, filename):
        r"""
        Export the polyhedron as a H-representation to a file.

        INPUT:

        - ``filename`` -- the output file.

        .. SEEALSO::

            :meth:`cdd_Hrepresentation` -- return the H-representation of the
            polyhedron as a string.

        EXAMPLES::

            sage: from sage.misc.temporary_file import tmp_filename
            sage: filename = tmp_filename(ext='.ext')
            sage: polytopes.cube().write_cdd_Hrepresentation(filename)
        """
        with open(filename, 'w') as f:
            f.write(self.cdd_Hrepresentation())

    def cdd_Vrepresentation(self):
        r"""
        Write the vertices/rays/lines data of the polyhedron in cdd's
        V-representation format.

        .. SEEALSO::

            :meth:`write_cdd_Vrepresentation` -- export the polyhedron as a
            V-representation to a file.

        OUTPUT: a string

        EXAMPLES::

            sage: q = Polyhedron(vertices = [[1,1],[0,0],[1,0],[0,1]])
            sage: print(q.cdd_Vrepresentation())
            V-representation
            begin
             4 3 rational
             1 0 0
             1 0 1
             1 1 0
             1 1 1
            end
        """
        from .cdd_file_format import cdd_Vrepresentation
        try:
            cdd_type = self._cdd_type
        except AttributeError:
            if self.base_ring() is ZZ or self.base_ring() is QQ:
                cdd_type = 'rational'
            elif self.base_ring() is RDF:
                cdd_type = 'real'
            else:
                raise TypeError('the base ring must be ZZ, QQ, or RDF')
        return cdd_Vrepresentation(cdd_type,
                                   list(self.vertex_generator()),
                                   list(self.ray_generator()),
                                   list(self.line_generator()))

    def write_cdd_Vrepresentation(self, filename):
        r"""
        Export the polyhedron as a V-representation to a file.

        INPUT:

        - ``filename`` -- the output file.

        .. SEEALSO::

            :meth:`cdd_Vrepresentation` -- return the V-representation of the
            polyhedron as a string.

        EXAMPLES::

            sage: from sage.misc.temporary_file import tmp_filename
            sage: filename = tmp_filename(ext='.ext')
            sage: polytopes.cube().write_cdd_Vrepresentation(filename)
        """
        with open(filename, 'w') as f:
            f.write(self.cdd_Vrepresentation())

    def to_linear_program(self, solver=None, return_variable=False, base_ring=None):
        r"""
        Return a linear optimization problem over the polyhedron in the form of
        a :class:`MixedIntegerLinearProgram`.

        INPUT:

        - ``solver`` -- select a solver (MIP backend). See the documentation
          of for :class:`MixedIntegerLinearProgram`. Set to ``None`` by default.

        - ``return_variable`` -- (default: ``False``) If ``True``, return a tuple
          ``(p, x)``, where ``p`` is the :class:`MixedIntegerLinearProgram` object
          and ``x`` is the vector-valued MIP variable in this problem, indexed
          from 0.  If ``False``, only return ``p``.

        - ``base_ring`` -- select a field over which the linear program should be
          set up.  Use ``RDF`` to request a fast inexact (floating point) solver
          even if ``self`` is exact.

        Note that the :class:`MixedIntegerLinearProgram` object will have the
        null function as an objective to be maximized.

        .. SEEALSO::

            :meth:`~MixedIntegerLinearProgram.polyhedron` -- return the
            polyhedron associated with a :class:`MixedIntegerLinearProgram`
            object.

        EXAMPLES:

        Exact rational linear program::

            sage: p = polytopes.cube()
            sage: p.to_linear_program()
            Linear Program (no objective, 3 variables, 6 constraints)
            sage: lp, x = p.to_linear_program(return_variable=True)
            sage: lp.set_objective(2*x[0] + 1*x[1] + 39*x[2])
            sage: lp.solve()
            42
            sage: lp.get_values(x[0], x[1], x[2])
            [1, 1, 1]

        Floating-point linear program::

            sage: lp, x = p.to_linear_program(return_variable=True, base_ring=RDF)
            sage: lp.set_objective(2*x[0] + 1*x[1] + 39*x[2])
            sage: lp.solve()
            42.0

        Irrational algebraic linear program over an embedded number field::

            sage: p = polytopes.icosahedron()                                           # optional - sage.rings.number_field
            sage: lp, x = p.to_linear_program(return_variable=True)                     # optional - sage.rings.number_field
            sage: lp.set_objective(x[0] + x[1] + x[2])                                  # optional - sage.rings.number_field
            sage: lp.solve()                                                            # optional - sage.rings.number_field
            1/4*sqrt5 + 3/4

        Same example with floating point::

            sage: lp, x = p.to_linear_program(return_variable=True, base_ring=RDF)      # optional - sage.rings.number_field
            sage: lp.set_objective(x[0] + x[1] + x[2])                                  # optional - sage.rings.number_field
            sage: lp.solve()                                               # tol 1e-5   # optional - sage.rings.number_field
            1.3090169943749475

        Same example with a specific floating point solver::

            sage: lp, x = p.to_linear_program(return_variable=True, solver='GLPK')      # optional - sage.rings.number_field
            sage: lp.set_objective(x[0] + x[1] + x[2])                                  # optional - sage.rings.number_field
            sage: lp.solve()                                               # tol 1e-8   # optional - sage.rings.number_field
            1.3090169943749475

        Irrational algebraic linear program over `AA`::

            sage: p = polytopes.icosahedron(base_ring=AA)                               # optional - sage.rings.number_field
            sage: lp, x = p.to_linear_program(return_variable=True)                     # optional - sage.rings.number_field
            sage: lp.set_objective(x[0] + x[1] + x[2])                                  # optional - sage.rings.number_field
            sage: lp.solve()                                               # long time  # optional - sage.rings.number_field
            1.309016994374948?

        TESTS::

            sage: p = polytopes.flow_polytope(digraphs.DeBruijn(3,2)); p                # optional - sage.graphs
            A 19-dimensional polyhedron in QQ^27
             defined as the convex hull of 1 vertex and 148 rays
            sage: p.to_linear_program().polyhedron() == p                               # optional - sage.graphs
            True

            sage: p = polytopes.icosahedron()                                           # optional - sage.rings.number_field
            sage: p.to_linear_program(solver='PPL')                                     # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            TypeError: The PPL backend only supports rational data.

        Test that equations are handled correctly (:trac:`24154`)::

            sage: p = Polyhedron(vertices=[[19]])
            sage: lp, x = p.to_linear_program(return_variable=True)
            sage: lp.set_objective(x[0])
            sage: lp.solve()
            19
        """
        if base_ring is None:
            base_ring = self.base_ring()
        base_ring = base_ring.fraction_field()
        from sage.numerical.mip import MixedIntegerLinearProgram
        p = MixedIntegerLinearProgram(solver=solver, base_ring=base_ring)
        x = p.new_variable(real=True, nonnegative=False)

        for ineqn in self.inequalities_list():
            b = -ineqn.pop(0)
            p.add_constraint(p.sum([x[i]*ineqn[i] for i in range(len(ineqn))]) >= b)

        for eqn in self.equations_list():
            b = -eqn.pop(0)
            p.add_constraint(p.sum([x[i]*eqn[i] for i in range(len(eqn))]) == b)

        if return_variable:
            return p, x
        else:
            return p

    def boundary_complex(self):
        """
        Return the simplicial complex given by the boundary faces of ``self``,
        if it is simplicial.

        OUTPUT:

        A (spherical) simplicial complex

        EXAMPLES:

        The boundary complex of the octahedron::

            sage: oc = polytopes.octahedron()
            sage: sc_oc = oc.boundary_complex()
            sage: fl_oc = oc.face_lattice()
            sage: fl_sc = sc_oc.face_poset()
            sage: [len(x) for x in fl_oc.level_sets()]
            [1, 6, 12, 8, 1]
            sage: [len(x) for x in fl_sc.level_sets()]
            [6, 12, 8]
            sage: sc_oc.euler_characteristic()
            2
            sage: sc_oc.homology()
            {0: 0, 1: 0, 2: Z}

        The polyhedron should be simplicial::

            sage: c = polytopes.cube()
            sage: c.boundary_complex()
            Traceback (most recent call last):
            ...
            NotImplementedError: this function is only implemented for simplicial polytopes

        TESTS::

            sage: p = Polyhedron(rays=[[1,1]])
            sage: p.boundary_complex()
            Traceback (most recent call last):
            ...
            ValueError: self should be compact
        """
        from sage.topology.simplicial_complex import SimplicialComplex
        if not self.is_compact():
            raise ValueError("self should be compact")

        if self.is_simplicial():
            inc_mat_cols = self.incidence_matrix().columns()
            ineq_indices = [inc_mat_cols[i].nonzero_positions()
                            for i in range(self.n_Hrepresentation())
                            if self.Hrepresentation()[i].is_inequality()]
            return SimplicialComplex(ineq_indices, maximality_check=False)
        else:
            raise NotImplementedError("this function is only implemented for simplicial polytopes")

    @cached_method
    def center(self):
        """
        Return the average of the vertices.

        .. SEEALSO::

            :meth:`sage.geometry.polyhedron.base1.Polyhedron_base1.representative_point`.

        OUTPUT:

        The center of the polyhedron. All rays and lines are
        ignored. Raises a ``ZeroDivisionError`` for the empty
        polytope.

        EXAMPLES::

            sage: p = polytopes.hypercube(3)
            sage: p = p + vector([1,0,0])
            sage: p.center()
            (1, 0, 0)
        """
        if self.dim() == 0:
            return self.vertices()[0].vector()
        else:
            vertex_sum = vector(self.base_ring(), [0]*self.ambient_dim())
            for v in self.vertex_generator():
                vertex_sum += v.vector()
            vertex_sum.set_immutable()
            return vertex_sum / self.n_vertices()

    @cached_method(do_pickle=True)
    def centroid(self, engine='auto', **kwds):
        r"""
        Return the center of the mass of the polytope.

        The mass is taken with respect to the induced Lebesgue measure,
        see :meth:`volume`.

        If the polyhedron is not compact, a ``NotImplementedError`` is
        raised.

        INPUT:

        - ``engine`` -- either 'auto' (default), 'internal',
          'TOPCOM', or 'normaliz'.  The 'internal' and 'TOPCOM' instruct
          this package to always use its own triangulation algorithms
          or TOPCOM's algorithms, respectively. By default ('auto'),
          TOPCOM is used if it is available and internal routines otherwise.

        - ``**kwds`` -- keyword arguments that are passed to the
          triangulation engine (see :meth:`triangulate`).

        OUTPUT: The centroid as vector.

        ALGORITHM:

        We triangulate the polytope and find the barycenter of the simplices.
        We add the individual barycenters weighted by the fraction of the total
        mass.

        EXAMPLES::

            sage: P = polytopes.hypercube(2).pyramid()
            sage: P.centroid()
            (1/4, 0, 0)

            sage: P = polytopes.associahedron(['A',2])
            sage: P.centroid()
            (2/21, 2/21)

            sage: P = polytopes.permutahedron(4, backend='normaliz')  # optional - pynormaliz
            sage: P.centroid()                                        # optional - pynormaliz
            (5/2, 5/2, 5/2, 5/2)

        The method is not implemented for unbounded polyhedra::

            sage: P = Polyhedron(vertices=[(0,0)],rays=[(1,0),(0,1)])
            sage: P.centroid()
            Traceback (most recent call last):
            ...
            NotImplementedError: the polyhedron is not compact

        The centroid of an empty polyhedron is not defined::

            sage: Polyhedron().centroid()
            Traceback (most recent call last):
            ...
            ZeroDivisionError: rational division by zero

        TESTS::

            sage: Polyhedron(vertices=[[0,1]]).centroid()
            (0, 1)
        """
        if not self.is_compact():
            raise NotImplementedError("the polyhedron is not compact")
        if self.n_vertices() == self.dim() + 1:
            # The centroid of a simplex is its center.
            return self.center()

        triangulation = self.triangulate(engine=engine, **kwds)

        if self.ambient_dim() == self.dim():
            pc = triangulation.point_configuration()
        else:
            from sage.geometry.triangulation.point_configuration import PointConfiguration
            A, b = self.affine_hull_projection(as_affine_map=True, orthogonal=True, orthonormal=True, extend=True)
            pc = PointConfiguration((A(v.vector()) for v in self.Vrep_generator()))

        barycenters = [sum(self.Vrepresentation(i).vector() for i in simplex)/(self.dim() + 1) for simplex in triangulation]
        volumes = [pc.volume(simplex) for simplex in triangulation]

        centroid = sum(volumes[i]*barycenters[i] for i in range(len(volumes)))/sum(volumes)
        if self.ambient_dim() != self.dim():
            # By the affine hull projection, the centroid has base ring ``AA``,
            # we try return the centroid in a reasonable ring.
            try:
                return centroid.change_ring(self.base_ring().fraction_field())
            except ValueError:
                pass
        return centroid

    @cached_method
    def radius_square(self):
        """
        Return the square of the maximal distance from the
        :meth:`center` to a vertex. All rays and lines are ignored.

        OUTPUT:

        The square of the radius, which is in :meth:`base_ring`.

        EXAMPLES::

            sage: p = polytopes.permutahedron(4, project = False)
            sage: p.radius_square()
            5
        """
        vertices = [v.vector() - self.center() for v in self.vertex_generator()]
        return max(v.dot_product(v) for v in vertices)

    def radius(self):
        """
        Return the maximal distance from the center to a vertex. All
        rays and lines are ignored.

        OUTPUT:

        The radius for a rational polyhedron is, in general, not
        rational.  use :meth:`radius_square` if you need a rational
        distance measure.

        EXAMPLES::

            sage: p = polytopes.hypercube(4)
            sage: p.radius()
            2
        """
        return self.radius_square().sqrt()

    def is_inscribed(self, certificate=False):
        """
        This function tests whether the vertices of the polyhedron are
        inscribed on a sphere.

        The polyhedron is expected to be compact and full-dimensional.
        A full-dimensional compact polytope is inscribed if there exists
        a point in space which is equidistant to all its vertices.

        ALGORITHM:

        The function first computes the circumsphere of a full-dimensional
        simplex with vertices of ``self``. It is found by lifting the points on a
        paraboloid to find the hyperplane on which the circumsphere is lifted.
        Then, it checks if all other vertices are equidistant to the
        circumcenter of that simplex.

        INPUT:

        - ``certificate`` -- (default: ``False``) boolean; specifies whether to
          return the circumcenter, if found.

        OUTPUT:

        If ``certificate`` is true, returns a tuple containing:

        1. Boolean.
        2. The circumcenter of the polytope or None.

        If ``certificate`` is false:

        - a Boolean.

        EXAMPLES::

            sage: q = Polyhedron(vertices = [[1,1,1,1],[-1,-1,1,1],[1,-1,-1,1],
            ....:                            [-1,1,-1,1],[1,1,1,-1],[-1,-1,1,-1],
            ....:                            [1,-1,-1,-1],[-1,1,-1,-1],[0,0,10/13,-24/13],
            ....:                            [0,0,-10/13,-24/13]])
            sage: q.is_inscribed(certificate=True)
            (True, (0, 0, 0, 0))

            sage: cube = polytopes.cube()
            sage: cube.is_inscribed()
            True

            sage: translated_cube = Polyhedron(vertices=[v.vector() + vector([1,2,3])
            ....:                                        for v in cube.vertices()])
            sage: translated_cube.is_inscribed(certificate=True)
            (True, (1, 2, 3))

            sage: truncated_cube = cube.face_truncation(cube.faces(0)[0])
            sage: truncated_cube.is_inscribed()
            False

        The method is not implemented for non-full-dimensional polytope or
        unbounded polyhedra::

            sage: square = Polyhedron(vertices=[[1,0,0],[0,1,0],[1,1,0],[0,0,0]])
            sage: square.is_inscribed()
            Traceback (most recent call last):
            ...
            NotImplementedError: this function is implemented for full-dimensional polyhedra only

            sage: p = Polyhedron(vertices=[(0,0)],rays=[(1,0),(0,1)])
            sage: p.is_inscribed()
            Traceback (most recent call last):
            ...
            NotImplementedError: this function is not implemented for unbounded polyhedra

        TESTS:

        We check that :trac:`28464` is fixed::

            sage: P = Polyhedron(vertices=[(-130658298093891402635075/416049251842505144482473,
            ....: 177469511761879509172000/1248147755527515433447419,
            ....: 485550543257132133136169/2496295511055030866894838,
            ....: 2010744967797898733758669/2496295511055030866894838),
            ....: (-146945725603929909850/706333405676769433081,
            ....: -84939725782618445000/706333405676769433081,
            ....: 560600045283000988081/1412666811353538866162,
            ....: 969778382942371268081/1412666811353538866162),
            ....: (-46275018824497300/140422338198040641,
            ....: -5747688262110000/46807446066013547, 1939357556329/7033601552658,
            ....: 1939357556329/7033601552658), (-17300/59929, -10000/59929, 39929/119858,
            ....: 39929/119858), (-4700/32209, -10000/32209, 12209/64418, 12209/64418),
            ....: (QQ(0), QQ(0), QQ(0), QQ(1)), (QQ(0), QQ(0), 1/2, 1/2), (300/10027,
            ....: -10000/30081, 10081/60162, 10081/60162), (112393975400/1900567733649,
            ....: 117311600000/633522577883, 43678681/95197362, 43678681/95197362),
            ....: (6109749955400/133380598418321, 37106807920000/133380598418321,
            ....: 2677964249/6680888498, 2677964249/6680888498),
            ....: (29197890764005600/402876806828660641,
            ....: -2150510776960000/402876806828660641,
            ....: 398575785274740641/805753613657321282,
            ....: 398575785274740641/805753613657321282),
            ....: (5576946899441759759983005325/110078073300232813237456943251,
            ....: -29071211718677797926570478000/110078073300232813237456943251,
            ....: 59439312069347378584317232001/220156146600465626474913886502,
            ....: 181346577228466312205473034501/220156146600465626474913886502),
            ....: (150040732779124914266530235300/6774574358246204311268446913881,
            ....: -2813827375989039189507000218000/6774574358246204311268446913881,
            ....: 1260217414021285074925933133881/13549148716492408622536893827762,
            ....: 3232518047094242684574253773881/13549148716492408622536893827762),
            ....: (3816349407976279597850158016285000/88842127448735433741180809504357161,
            ....: 27965821247423216557301387453968000/88842127448735433741180809504357161,
            ....: 68546256000224819256028677086357161/177684254897470867482361619008714322,
            ....: 86062257922545755787315412690197161/177684254897470867482361619008714322)])
            sage: P.is_inscribed()
            True

            sage: P = Polyhedron(vertices=[[0, -1, 0, 0],
            ....:                          [0, 0, -1, 0],
            ....:                          [0, 0, 0, -1],
            ....:                          [0, 0, +1, 0],
            ....:                          [0, 0, 0, +1],
            ....:                          [+1, 0, 0, 0]])
            sage: P.is_inscribed()
            True

        We check that :trac:`29125` is fixed::

            sage: P = Polyhedron(vertices=[[-2,-1], [-2,1], [0,-1], [0,1]], backend='field')
            sage: P.is_inscribed()
            True
            sage: V = P.Vrepresentation()
            sage: H = P.Hrepresentation()
            sage: parent = P.parent()
            sage: for V1 in Permutations(V):                                    # optional - sage.combinat
            ....:     P1 = parent._element_constructor_(
            ....:         [V1, [], []], [H, []], Vrep_minimal=True, Hrep_minimal=True)
            ....:     assert P1.is_inscribed()
        """

        if not self.is_compact():
            raise NotImplementedError("this function is not implemented for unbounded polyhedra")

        if not self.is_full_dimensional():
            raise NotImplementedError("this function is implemented for full-dimensional polyhedra only")

        dimension = self.dimension()
        vertices = self.vertices()

        # We obtain vertices that are an affine basis of the affine hull.
        affine_basis = self.an_affine_basis()
        raw_data = []
        for vertex in affine_basis:
            vertex_vector = vertex.vector()
            raw_data += [[sum(i**2 for i in vertex_vector)] +
                         [i for i in vertex_vector] + [1]]
        matrix_data = matrix(raw_data)

        # The determinant "a" should not be zero because
        # the vertices in ``affine_basis`` are an affine basis.
        a = matrix_data.matrix_from_columns(range(1, dimension+2)).determinant()

        minors = [(-1)**(i)*matrix_data.matrix_from_columns([j for j in range(dimension+2) if j != i]).determinant()
                  for i in range(1, dimension+1)]
        c = (-1)**(dimension+1)*matrix_data.matrix_from_columns(range(dimension+1)).determinant()

        circumcenter = vector([minors[i]/(2*a) for i in range(dimension)])
        squared_circumradius = (sum(m**2 for m in minors) - 4 * a * c) / (4*a**2)

        # Checking if the circumcenter has the correct sign
        if not all(sum(i**2 for i in v.vector() - circumcenter) == squared_circumradius
                   for v in vertices if v in affine_basis):
            circumcenter = - circumcenter

        is_inscribed = all(sum(i**2 for i in v.vector() - circumcenter) == squared_circumradius
                           for v in vertices if v not in affine_basis)

        if certificate:
            if is_inscribed:
                return (True, circumcenter)
            else:
                return (False, None)
        else:
            return is_inscribed

    def hyperplane_arrangement(self):
        """
        Return the hyperplane arrangement defined by the equations and
        inequalities.

        OUTPUT:

        A :class:`hyperplane arrangement
        <sage.geometry.hyperplane_arrangement.arrangement.HyperplaneArrangementElement>`
        consisting of the hyperplanes defined by the
        :meth:`Hrepresentation`.
        If the polytope is full-dimensional, this is the hyperplane
        arrangement spanned by the facets of the polyhedron.

        EXAMPLES::

            sage: p = polytopes.hypercube(2)
            sage: p.hyperplane_arrangement()
            Arrangement <-t0 + 1 | -t1 + 1 | t1 + 1 | t0 + 1>
        """
        names = tuple('t' + str(i) for i in range(self.ambient_dim()))
        from sage.geometry.hyperplane_arrangement.arrangement import HyperplaneArrangements
        field = self.base_ring().fraction_field()
        H = HyperplaneArrangements(field, names)
        return H(self)

    @cached_method
    def gale_transform(self):
        """
        Return the Gale transform of a polytope as described in the
        reference below.

        OUTPUT:

        A list of vectors, the Gale transform.  The dimension is the
        dimension of the affine dependencies of the vertices of the
        polytope.

        EXAMPLES:

        This is from the reference, for a triangular prism::

            sage: p = Polyhedron(vertices = [[0,0],[0,1],[1,0]])
            sage: p2 = p.prism()
            sage: p2.gale_transform()
            ((-1, 0), (0, -1), (1, 1), (-1, -1), (1, 0), (0, 1))

        REFERENCES:

            Lectures in Geometric Combinatorics, R.R.Thomas, 2006, AMS Press.

        .. SEEALSO::

            :func`~sage.geometry.polyhedron.library.gale_transform_to_polyhedron`.

        TESTS::

            sage: P = Polyhedron(rays=[[1,0,0]])
            sage: P.gale_transform()
            Traceback (most recent call last):
            ...
            ValueError: not a polytope

        Check that :trac:`29073` is fixed::

            sage: P = polytopes.icosahedron(exact=False)
            sage: sum(P.gale_transform()).norm() < 1e-15
            True
        """
        if not self.is_compact():
            raise ValueError('not a polytope')

        A = matrix(self.n_vertices(),
                   [[1]+x for x in self.vertex_generator()])
        A = A.transpose()
        A_ker = A.right_kernel_matrix(basis='computed')
        return tuple(A_ker.columns())

    def _test_gale_transform(self, tester=None, **options):
        """
        Run tests on the method :meth:`.gale_transform` and its inverse
        :meth:`~sage.geometry.polyhedron.library.gale_transform_to_polytope`.

        TESTS::

            sage: polytopes.cross_polytope(3)._test_gale_transform()
        """
        if tester is None:
            tester = self._tester(**options)

        if not self.is_compact():
            with tester.assertRaises(ValueError):
                self.gale_transform()
            return

        # Check :trac:`29073`.
        if not self.base_ring().is_exact() and self.ambient_dim() > 0:
            g = self.gale_transform()
            tester.assertTrue(sum(g).norm() < 1e-10 or sum(g).norm()/matrix(g).norm() < 1e-13)
            return

        # Prevent very long doctests.
        if self.n_vertices() + self.n_rays() > 50 or self.n_facets() > 50:
            return

        if not self.is_empty():
            # ``gale_transform_to_polytope`` needs at least one vertex to work.
            from sage.geometry.polyhedron.library import gale_transform_to_polytope
            g = self.gale_transform()
            P = gale_transform_to_polytope(g, base_ring=self.base_ring(), backend=self.backend())

            try:
                import sage.graphs.graph
            except ImportError:
                pass
            else:
                tester.assertTrue(self.is_combinatorially_isomorphic(P))

    @cached_method
    def normal_fan(self, direction='inner'):
        r"""
        Return the normal fan of a compact full-dimensional rational polyhedron.

        This returns the inner normal fan of ``self``. For the outer normal fan,
        use ``direction='outer'``.

        INPUT:

        - ``direction`` -- either ``'inner'`` (default) or ``'outer'``; if
          set to ``'inner'``, use the inner normal vectors to span the cones of
          the fan, if set to ``'outer'``, use the outer normal vectors.

        OUTPUT:

        A complete fan of the ambient space as a
        :class:`~sage.geometry.fan.RationalPolyhedralFan`.

        .. SEEALSO::

            :meth:`face_fan`.

        EXAMPLES::

            sage: S = Polyhedron(vertices = [[0, 0], [1, 0], [0, 1]])
            sage: S.normal_fan()
            Rational polyhedral fan in 2-d lattice N

            sage: C = polytopes.hypercube(4)
            sage: NF = C.normal_fan(); NF
            Rational polyhedral fan in 4-d lattice N

        Currently, it is only possible to get the normal fan of a bounded rational polytope::

            sage: P = Polyhedron(rays = [[1, 0], [0, 1]])
            sage: P.normal_fan()
            Traceback (most recent call last):
            ...
            NotImplementedError: the normal fan is only supported for polytopes (compact polyhedra).

            sage: Q = Polyhedron(vertices = [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            sage: Q.normal_fan()
            Traceback (most recent call last):
            ...
            ValueError: the normal fan is only defined for full-dimensional polytopes

            sage: R = Polyhedron(vertices=[[0, 0], [AA(sqrt(2)), 0], [0, AA(sqrt(2))]])   # optional - sage.rings.number_field
            sage: R.normal_fan()                                                          # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            NotImplementedError: normal fan handles only polytopes over the rationals

            sage: P = Polyhedron(vertices=[[0,0],[2,0],[0,2],[2,1],[1,2]])
            sage: P.normal_fan(direction=None)
            Traceback (most recent call last):
            ...
            TypeError: the direction should be 'inner' or 'outer'

            sage: inner_nf = P.normal_fan()
            sage: inner_nf.rays()
            N( 1,  0),
            N( 0, -1),
            N( 0,  1),
            N(-1,  0),
            N(-1, -1)
            in 2-d lattice N

            sage: outer_nf = P.normal_fan(direction='outer')
            sage: outer_nf.rays()
            N( 1,  0),
            N( 1,  1),
            N( 0,  1),
            N(-1,  0),
            N( 0, -1)
            in 2-d lattice N

        REFERENCES:

        For more information, see Chapter 7 of [Zie2007]_.
        """
        from sage.geometry.fan import NormalFan

        if not QQ.has_coerce_map_from(self.base_ring()):
            raise NotImplementedError('normal fan handles only polytopes over the rationals')
        if direction == 'inner':
            return NormalFan(self)
        elif direction == 'outer':
            return NormalFan(-self)
        else:
            raise TypeError("the direction should be 'inner' or 'outer'")

    @cached_method
    def face_fan(self):
        r"""
        Return the face fan of a compact rational polyhedron.

        OUTPUT:

        A fan of the ambient space as a
        :class:`~sage.geometry.fan.RationalPolyhedralFan`.

        .. SEEALSO::

            :meth:`normal_fan`.

        EXAMPLES::

            sage: T = polytopes.cuboctahedron()
            sage: T.face_fan()
            Rational polyhedral fan in 3-d lattice M

        The polytope should contain the origin in the interior::

            sage: P = Polyhedron(vertices = [[1/2, 1], [1, 1/2]])
            sage: P.face_fan()
            Traceback (most recent call last):
            ...
            ValueError: face fans are defined only for polytopes containing the origin as an interior point!

            sage: Q = Polyhedron(vertices = [[-1, 1/2], [1, -1/2]])
            sage: Q.contains([0,0])
            True
            sage: FF = Q.face_fan(); FF
            Rational polyhedral fan in 2-d lattice M

        The polytope has to have rational coordinates::

            sage: S = polytopes.dodecahedron()                                # optional - sage.rings.number_field
            sage: S.face_fan()                                                # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            NotImplementedError: face fan handles only polytopes over the rationals

        REFERENCES:

        For more information, see Chapter 7 of [Zie2007]_.
        """
        from sage.geometry.fan import FaceFan

        if not QQ.has_coerce_map_from(self.base_ring()):
            raise NotImplementedError('face fan handles only polytopes over the rationals')

        return FaceFan(self)

    def _triangulate_normaliz(self):
        r"""
        Gives a triangulation of the polyhedron using normaliz

        OUTPUT:

        A tuple of pairs ``(simplex,simplex_volume)`` used in the
        triangulation.

        .. NOTE::

            This function depends on Normaliz (i.e. the ``pynormaliz`` optional
            package). See the Normaliz documentation for further details.

        TESTS::

            sage: K = Polyhedron(vertices=[[1,1]], rays=[[1,0],[1,2]])
            sage: K._triangulate_normaliz()
            Traceback (most recent call last):
            ...
            TypeError: the polyhedron's backend should be 'normaliz'
        """
        raise TypeError("the polyhedron's backend should be 'normaliz'")

    def triangulate(self, engine='auto', connected=True, fine=False, regular=None, star=None):
        r"""
        Return a triangulation of the polytope.

        INPUT:

        - ``engine`` -- either 'auto' (default), 'internal',
          'TOPCOM', or 'normaliz'.  The 'internal' and 'TOPCOM' instruct
          this package to always use its own triangulation algorithms
          or TOPCOM's algorithms, respectively. By default ('auto'),
          TOPCOM is used if it is available and internal routines otherwise.

        The remaining keyword parameters are passed through to the
        :class:`~sage.geometry.triangulation.point_configuration.PointConfiguration`
        constructor:

        - ``connected`` -- boolean (default: ``True``). Whether the
          triangulations should be connected to the regular
          triangulations via bistellar flips. These are much easier to
          compute than all triangulations.

        - ``fine`` -- boolean (default: ``False``). Whether the
          triangulations must be fine, that is, make use of all points
          of the configuration.

        - ``regular`` -- boolean or ``None`` (default:
          ``None``). Whether the triangulations must be regular. A
          regular triangulation is one that is induced by a
          piecewise-linear convex support function. In other words,
          the shadows of the faces of a polyhedron in one higher
          dimension.

          * ``True``: Only regular triangulations.

          * ``False``: Only non-regular triangulations.

          * ``None`` (default): Both kinds of triangulation.

        - ``star`` -- either ``None`` (default) or a point. Whether
          the triangulations must be star. A triangulation is star if
          all maximal simplices contain a common point. The central
          point can be specified by its index (an integer) in the
          given points or by its coordinates (anything iterable.)

        OUTPUT:

        A triangulation of the convex hull of the vertices as a
        :class:`~sage.geometry.triangulation.point_configuration.Triangulation`. The
        indices in the triangulation correspond to the
        :meth:`Vrepresentation` objects.

        EXAMPLES::

            sage: cube = polytopes.hypercube(3)
            sage: triangulation = cube.triangulate(
            ....:    engine='internal') # to make doctest independent of TOPCOM
            sage: triangulation
            (<0,1,2,7>, <0,1,5,7>, <0,2,3,7>, <0,3,4,7>, <0,4,5,7>, <1,5,6,7>)
            sage: simplex_indices = triangulation[0]; simplex_indices
            (0, 1, 2, 7)
            sage: simplex_vertices = [ cube.Vrepresentation(i) for i in simplex_indices ]
            sage: simplex_vertices
            [A vertex at (1, -1, -1),
             A vertex at (1, 1, -1),
             A vertex at (1, 1, 1),
             A vertex at (-1, 1, 1)]
            sage: Polyhedron(simplex_vertices)
            A 3-dimensional polyhedron in ZZ^3 defined as the convex hull of 4 vertices

        It is possible to use ``'normaliz'`` as an engine. For this, the
        polyhedron should have the backend set to normaliz::

            sage: P = Polyhedron(vertices=[[0,0,1],[1,0,1],[0,1,1],[1,1,1]],backend='normaliz')  # optional - pynormaliz
            sage: P.triangulate(engine='normaliz')  # optional - pynormaliz
            (<0,1,2>, <1,2,3>)

            sage: P = Polyhedron(vertices=[[0,0,1],[1,0,1],[0,1,1],[1,1,1]])
            sage: P.triangulate(engine='normaliz')
            Traceback (most recent call last):
            ...
            TypeError: the polyhedron's backend should be 'normaliz'

        The normaliz engine can triangulate pointed cones::

            sage: C1 = Polyhedron(rays=[[0,0,1],[1,0,1],[0,1,1],[1,1,1]],backend='normaliz')  # optional - pynormaliz
            sage: C1.triangulate(engine='normaliz')  # optional - pynormaliz
            (<0,1,2>, <1,2,3>)
            sage: C2 = Polyhedron(rays=[[1,0,1],[0,0,1],[0,1,1],[1,1,10/9]],backend='normaliz')  # optional - pynormaliz
            sage: C2.triangulate(engine='normaliz')  # optional - pynormaliz
            (<0,1,2>, <1,2,3>)

        They can also be affine cones::

            sage: K = Polyhedron(vertices=[[1,1,1]],rays=[[1,0,0],[0,1,0],[1,1,-1],[1,1,1]], backend='normaliz')  # optional - pynormaliz
            sage: K.triangulate(engine='normaliz')  # optional - pynormaliz
            (<0,1,2>, <0,1,3>)
        """
        if self.lines():
            raise NotImplementedError('triangulation of polyhedra with lines is not supported')
        if len(self.vertices_list()) >= 2 and self.rays_list():
            raise NotImplementedError('triangulation of non-compact polyhedra that are not cones is not supported')
        if not self.is_compact() and engine != 'normaliz':
            raise NotImplementedError("triangulation of pointed polyhedra requires 'normaliz'")
        from sage.geometry.triangulation.point_configuration import PointConfiguration
        if self.is_compact():
            pc = PointConfiguration((v.vector() for v in self.vertex_generator()),
                                    connected=connected, fine=fine, regular=regular, star=star)
            # If the engine is not normaliz, we pass directly to the
            # PointConfiguration module.
            if engine != 'normaliz':
                pc.set_engine(engine)
                return pc.triangulate()
            else:
                return pc(self._triangulate_normaliz())
        else:  # From above, we have a pointed cone and the engine is normaliz
            try:
                pc = PointConfiguration((v.vector() for v in self.ray_generator()),
                                        connected=connected, fine=fine, regular=regular, star=star)
                return pc(self._triangulate_normaliz())
            except AssertionError:
                # PointConfiguration is not adapted to inhomogeneous cones
                # This is a hack. TODO: Implement the necessary things in
                # PointConfiguration to accept such cases.
                c = self.representative_point()
                normed_v = ((1/(r.vector()*c))*r.vector() for r in self.ray_generator())
                pc = PointConfiguration(normed_v, connected=connected, fine=fine, regular=regular, star=star)
                return pc(self._triangulate_normaliz())

    def is_minkowski_summand(self, Y):
        r"""
        Test whether ``Y`` is a Minkowski summand.

        See :meth:`minkowski_sum`.

        OUTPUT:

        Boolean. Whether there exists another polyhedron `Z` such that
        ``self`` can be written as `Y\oplus Z`.

        EXAMPLES::

            sage: A = polytopes.hypercube(2)
            sage: B = Polyhedron(vertices=[(0,1), (1/2,1)])
            sage: C = Polyhedron(vertices=[(1,1)])
            sage: A.is_minkowski_summand(B)
            True
            sage: A.is_minkowski_summand(C)
            True
            sage: B.is_minkowski_summand(C)
            True
            sage: B.is_minkowski_summand(A)
            False
            sage: C.is_minkowski_summand(A)
            False
            sage: C.is_minkowski_summand(B)
            False
        """
        return self.minkowski_difference(Y).minkowski_sum(Y) == self

    def barycentric_subdivision(self, subdivision_frac=None):
        r"""
        Return the barycentric subdivision of a compact polyhedron.

        DEFINITION:

        The barycentric subdivision of a compact polyhedron is a standard way
        to triangulate its faces in such a way that maximal faces correspond to
        flags of faces of the starting polyhedron (i.e. a maximal chain in the
        face lattice of the polyhedron). As a simplicial complex, this is known
        as the order complex of the face lattice of the polyhedron.

        REFERENCE:

        See :wikipedia:`Barycentric_subdivision`
        Section 6.6, Handbook of Convex Geometry, Volume A, edited by P.M. Gruber and J.M.
        Wills. 1993, North-Holland Publishing Co..

        INPUT:

        - ``subdivision_frac`` -- number. Gives the proportion how far the new
          vertices are pulled out of the polytope. Default is `\frac{1}{3}` and
          the value should be smaller than `\frac{1}{2}`. The subdivision is
          computed on the polar polyhedron.

        OUTPUT:

        A Polyhedron object, subdivided as described above.

        EXAMPLES::

            sage: P = polytopes.hypercube(3)
            sage: P.barycentric_subdivision()
            A 3-dimensional polyhedron in QQ^3 defined as the convex hull
            of 26 vertices
            sage: P = Polyhedron(vertices=[[0,0,0],[0,1,0],[1,0,0],[0,0,1]])
            sage: P.barycentric_subdivision()
            A 3-dimensional polyhedron in QQ^3 defined as the convex hull
            of 14 vertices
            sage: P = Polyhedron(vertices=[[0,1,0],[0,0,1],[1,0,0]])
            sage: P.barycentric_subdivision()
            A 2-dimensional polyhedron in QQ^3 defined as the convex hull
            of 6 vertices
            sage: P = polytopes.regular_polygon(4, base_ring=QQ)                # optional - sage.rings.number_field
            sage: P.barycentric_subdivision()                                   # optional - sage.rings.number_field
            A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 8
            vertices

        TESTS::

            sage: P.barycentric_subdivision(1/2)
            Traceback (most recent call last):
            ...
            ValueError: the subdivision fraction should be between 0 and 1/2
            sage: P = Polyhedron(ieqs=[[1,0,1],[0,1,0],[1,0,0],[0,0,1]])
            sage: P.barycentric_subdivision()
            Traceback (most recent call last):
            ...
            ValueError: the polytope has to be compact
            sage: P = Polyhedron(vertices=[[0,0,0],[0,1,0],[1,0,0],[0,0,1]], backend='field')
            sage: P.barycentric_subdivision()
            A 3-dimensional polyhedron in QQ^3 defined as the convex hull of 14 vertices

            sage: polytopes.simplex(backend='field').barycentric_subdivision().backend()
            'field'
            sage: polytopes.cube(backend='cdd').barycentric_subdivision().backend()
            'cdd'
        """
        if subdivision_frac is None:
            subdivision_frac = ZZ.one() / 3

        if not self.is_compact():
            raise ValueError("the polytope has to be compact")
        if not (0 < subdivision_frac < ZZ.one() / 2):
            raise ValueError("the subdivision fraction should be "
                             "between 0 and 1/2")

        barycenter = self.center()
        parent = self.parent().base_extend(subdivision_frac)

        start_polar = (self - barycenter).polar(in_affine_span=True)
        polar = (self - barycenter).polar(in_affine_span=True)

        for i in range(self.dimension() - 1):

            new_ineq = []
            subdivided_faces = list(start_polar.faces(i))
            Hrep = polar.Hrepresentation()

            for face in subdivided_faces:

                face_vertices = face.vertices()
                normal_vectors = []

                for facet in Hrep:
                    if all(facet.contains(v) and not facet.interior_contains(v)
                           for v in face_vertices):
                        # The facet contains the face
                        normal_vectors.append(facet.A())

                normal_vector = sum(normal_vectors)
                B = - normal_vector * (face_vertices[0].vector())
                linear_evaluation = set([-normal_vector * (v.vector())
                                         for v in polar.vertices()])

                if B == max(linear_evaluation):
                    C = max(linear_evaluation.difference(set([B])))
                else:
                    C = min(linear_evaluation.difference(set([B])))

                ineq_vector = [(1 - subdivision_frac) * B + subdivision_frac * C] + list(normal_vector)
                new_ineq += [ineq_vector]

            new_ieqs = polar.inequalities_list() + new_ineq
            new_eqns = polar.equations_list()

            polar = parent.element_class(parent, None, [new_ieqs, new_eqns])

        return (polar.polar(in_affine_span=True)) + barycenter

    def projection(self, projection=None):
        """
        Return a projection object.

        INPUT:

        - ``proj`` -- a projection function

        OUTPUT:

        The identity projection. This is useful for plotting
        polyhedra.

        .. SEEALSO::

            :meth:`~sage.geometry.polyhedron.base.Polyhedron_base.schlegel_projection` for a more interesting projection.

        EXAMPLES::

            sage: p = polytopes.hypercube(3)
            sage: proj = p.projection()
            sage: proj
            The projection of a polyhedron into 3 dimensions
        """
        from .plot import Projection
        if projection is not None:
            self.projection = Projection(self, projection)
        else:
            self.projection = Projection(self)
        return self.projection

    def render_solid(self, **kwds):
        """
        Return a solid rendering of a 2- or 3-d polytope.

        EXAMPLES::

            sage: p = polytopes.hypercube(3)
            sage: p_solid = p.render_solid(opacity = .7)
            sage: type(p_solid)
            <class 'sage.plot.plot3d.index_face_set.IndexFaceSet'>
        """
        proj = self.projection()
        if self.ambient_dim() == 3:
            return proj.render_solid_3d(**kwds)
        if self.ambient_dim() == 2:
            return proj.render_fill_2d(**kwds)
        raise ValueError("render_solid is only defined for 2 and 3 dimensional polyhedra")

    def render_wireframe(self, **kwds):
        """
        For polytopes in 2 or 3 dimensions, return the edges
        as a list of lines.

        EXAMPLES::

            sage: p = Polyhedron([[1,2,],[1,1],[0,0]])
            sage: p_wireframe = p.render_wireframe()
            sage: p_wireframe._objects
            [Line defined by 2 points, Line defined by 2 points, Line defined by 2 points]
        """
        proj = self.projection()
        if self.ambient_dim() == 3:
            return proj.render_wireframe_3d(**kwds)
        if self.ambient_dim() == 2:
            return proj.render_outline_2d(**kwds)
        raise ValueError("render_wireframe is only defined for 2 and 3 dimensional polyhedra")

    def schlegel_projection(self, facet=None, position=None):
        """
        Return the Schlegel projection.

        * The facet is orthonormally transformed into its affine hull.

        * The position specifies a point coming out of the barycenter of the
          facet from which the other vertices will be projected into the facet.

        INPUT:

        - ``facet`` -- a PolyhedronFace. The facet into which the Schlegel
          diagram is created. The default is the first facet.

        - ``position`` -- a positive number. Determines a relative distance
          from the barycenter of ``facet``. A value close to 0 will place the
          projection point close to the facet and a large value further away.
          Default is `1`. If the given value is too large, an error is returned.

        OUTPUT:

        A :class:`~sage.geometry.polyhedron.plot.Projection` object.

        EXAMPLES::

            sage: p = polytopes.hypercube(3)
            sage: sch_proj = p.schlegel_projection()
            sage: schlegel_edge_indices = sch_proj.lines
            sage: schlegel_edges = [sch_proj.coordinates_of(x) for x in schlegel_edge_indices]
            sage: len([x for x in schlegel_edges if x[0][0] > 0])
            8

        The Schlegel projection preserves the convexity of facets, see :trac:`30015`::

            sage: fcube = polytopes.hypercube(4)
            sage: tfcube = fcube.face_truncation(fcube.faces(0)[0])
            sage: tfcube.facets()[-1]
            A 3-dimensional face of a Polyhedron in QQ^4 defined as the convex hull of 8 vertices
            sage: sp = tfcube.schlegel_projection(tfcube.facets()[-1])
            sage: sp.plot()  # optional - sage.plot
            Graphics3d Object

        The same truncated cube but see inside the tetrahedral facet::

            sage: tfcube.facets()[4]
            A 3-dimensional face of a Polyhedron in QQ^4 defined as the convex hull of 4 vertices
            sage: sp = tfcube.schlegel_projection(tfcube.facets()[4])
            sage: sp.plot()  # optional - sage.plot
            Graphics3d Object

        A different values of ``position`` changes the projection::

            sage: sp = tfcube.schlegel_projection(tfcube.facets()[4],1/2)
            sage: sp.plot()  # optional - sage.plot
            Graphics3d Object
            sage: sp = tfcube.schlegel_projection(tfcube.facets()[4],4)
            sage: sp.plot()  # optional - sage.plot
            Graphics3d Object

        A value which is too large give a projection point that sees more than
        one facet resulting in a error::

            sage: sp = tfcube.schlegel_projection(tfcube.facets()[4],5)
            Traceback (most recent call last):
            ...
            ValueError: the chosen position is too large
        """
        proj = self.projection()
        return proj.schlegel(facet, position)

    def _volume_lrs(self, verbose=False):
        """
        Computes the volume of a polytope using lrs.

        OUTPUT:

        The volume, cast to RDF (although lrs seems to output a
        rational value this must be an approximation in some cases).

        EXAMPLES::

            sage: polytopes.hypercube(3)._volume_lrs() # optional - lrslib
            8.0
            sage: (polytopes.hypercube(3)*2)._volume_lrs() # optional - lrslib
            64.0
            sage: polytopes.twenty_four_cell()._volume_lrs() # optional - lrslib
            2.0

        REFERENCES:

        - David Avis's lrs program.
        """
        from sage.features.lrs import Lrs
        Lrs().require()

        from sage.misc.temporary_file import tmp_filename
        from subprocess import Popen, PIPE

        in_str = self.cdd_Vrepresentation()
        in_str += 'volume'
        in_filename = tmp_filename()
        in_file = open(in_filename, 'w')
        in_file.write(in_str)
        in_file.close()
        if verbose:
            print(in_str)

        lrs_procs = Popen(['lrs', in_filename],
                          stdin=PIPE, stdout=PIPE, stderr=PIPE)
        ans, err = lrs_procs.communicate()
        ans = bytes_to_str(ans)
        err = bytes_to_str(err)
        if verbose:
            print(ans)
        # FIXME: check err

        for a_line in ans.splitlines():
            if 'Volume=' in a_line:
                volume = a_line.split('Volume=')[1]
                volume = RDF(QQ(volume))
                return volume

        raise ValueError("lrs did not return a volume")

    def _volume_latte(self, verbose=False, algorithm='triangulate', **kwargs):
        """
        Computes the volume of a polytope using LattE integrale.

        INPUT:

        - ``arg`` -- a cdd or LattE description string

        - ``algorithm`` -- (default: 'triangulate') the integration method. Use 'triangulate' for
          polytope triangulation or 'cone-decompose' for tangent cone decomposition method.

        - ``raw_output`` -- if ``True`` then return directly the output string from LattE.

        - ``verbose`` -- if ``True`` then return directly verbose output from LattE.

        - For all other options, consult the LattE manual.

        OUTPUT:

        A rational value, or a string if ``raw_output`` if set to ``True``.

        .. NOTE::

            This function depends on LattE (i.e., the ``latte_int`` optional
            package). See the LattE documentation for further details.

        EXAMPLES::

            sage: polytopes.hypercube(3)._volume_latte() # optional - latte_int
            8
            sage: (polytopes.hypercube(3)*2)._volume_latte() # optional - latte_int
            64
            sage: polytopes.twenty_four_cell()._volume_latte() # optional - latte_int
            2
            sage: polytopes.cuboctahedron()._volume_latte() # optional - latte_int
            20/3

        TESTS:

        Testing triangulate algorithm::

            sage: polytopes.cuboctahedron()._volume_latte(algorithm='triangulate') # optional - latte_int
            20/3

        Testing cone decomposition algorithm::

            sage: polytopes.cuboctahedron()._volume_latte(algorithm='cone-decompose') # optional - latte_int
            20/3

        Testing raw output::

            sage: polytopes.cuboctahedron()._volume_latte(raw_output=True) # optional - latte_int
            '20/3'

        Testing inexact rings::

            sage: P = Polyhedron(vertices=[[0,0],[1,0],[0,1]],base_ring=RDF)
            sage: P.volume(engine='latte')
            Traceback (most recent call last):
            ...
            ValueError: LattE integrale cannot be applied over inexact rings
        """
        from sage.interfaces.latte import integrate
        if self.base_ring() == RDF:
            raise ValueError("LattE integrale cannot be applied over inexact rings")
        else:
            return integrate(self.cdd_Hrepresentation(), algorithm=algorithm, cdd=True, verbose=verbose, **kwargs)

    def _volume_normaliz(self, measure='induced'):
        r"""
        Computes the volume of a polytope using normaliz.

        INPUT:

        - ``measure`` -- (default: 'induced') the measure to take. 'induced'
          correspond to ``EuclideanVolume`` in normaliz and 'induced_lattice'
          correspond to ``Volume`` in normaliz

        OUTPUT:

        A float value (when ``measure`` is 'induced') or a rational number
        (when ``measure`` is 'induced_lattice')

        .. NOTE::

            This function depends on Normaliz (i.e., the ``pynormaliz`` optional
            package). See the Normaliz documentation for further details.

        TESTS::

            sage: P = Polyhedron(vertices=[[0,0],[1,0],[0,1],[1,1]])
            sage: P._volume_normaliz()
            Traceback (most recent call last):
            ...
            TypeError: the backend should be normaliz
        """
        raise TypeError("the backend should be normaliz")

    @cached_method(do_pickle=True)
    def volume(self, measure='ambient', engine='auto', **kwds):
        """
        Return the volume of the polytope.

        INPUT:

        - ``measure`` -- string. The measure to use. Allowed values are:

          * ``ambient`` (default): Lebesgue measure of ambient space (volume)
          * ``induced``: Lebesgue measure of the affine hull (relative volume)
          * ``induced_rational``: Scaling of the Lebesgue measure for rational
            polytopes, such that the unit hypercube has volume 1
          * ``induced_lattice``: Scaling of the Lebesgue measure, such that the
            volume of the hypercube is factorial(n)

        - ``engine`` -- string. The backend to use. Allowed values are:

          * ``'auto'`` (default): choose engine according to measure
          * ``'internal'``: see :meth:`triangulate`
          * ``'TOPCOM'``: see :meth:`triangulate`
          * ``'lrs'``: use David Avis's lrs program (optional)
          * ``'latte'``: use LattE integrale program (optional)
          * ``'normaliz'``: use Normaliz program (optional)

        - ``**kwds`` -- keyword arguments that are passed to the
          triangulation engine

        OUTPUT:

        The volume of the polytope

        EXAMPLES::

            sage: polytopes.hypercube(3).volume()
            8
            sage: (polytopes.hypercube(3)*2).volume()
            64
            sage: polytopes.twenty_four_cell().volume()
            2

        Volume of the same polytopes, using the optional package lrslib
        (which requires a rational polytope).  For mysterious historical
        reasons, Sage casts lrs's exact answer to a float::

            sage: I3 = polytopes.hypercube(3)
            sage: I3.volume(engine='lrs') # optional - lrslib
            8.0
            sage: C24 = polytopes.twenty_four_cell()
            sage: C24.volume(engine='lrs') # optional - lrslib
            2.0

        If the base ring is exact, the answer is exact::

            sage: P5 = polytopes.regular_polygon(5)                             # optional - sage.rings.number_field
            sage: P5.volume()                                                   # optional - sage.rings.number_field
            2.377641290737884?

            sage: polytopes.icosahedron().volume()                              # optional - sage.rings.number_field
            5/12*sqrt5 + 5/4
            sage: numerical_approx(_) # abs tol 1e9                             # optional - sage.rings.number_field
            2.18169499062491

        When considering lower-dimensional polytopes, we can ask for the
        ambient (full-dimensional), the induced measure (of the affine
        hull) or, in the case of lattice polytopes, for the induced rational measure.
        This is controlled by the parameter `measure`. Different engines
        may have different ideas on the definition of volume of a
        lower-dimensional object::

            sage: P = Polyhedron([[0, 0], [1, 1]])
            sage: P.volume()
            0
            sage: P.volume(measure='induced')
            1.414213562373095?
            sage: P.volume(measure='induced_rational') # optional -- latte_int
            1

            sage: S = polytopes.regular_polygon(6); S                           # optional - sage.rings.number_field
            A 2-dimensional polyhedron in AA^2 defined as the convex hull of 6 vertices
            sage: edge = S.faces(1)[4].as_polyhedron()                          # optional - sage.rings.number_field
            sage: edge.vertices()                                               # optional - sage.rings.number_field
            (A vertex at (0.866025403784439?, 1/2), A vertex at (0, 1))
            sage: edge.volume()                                                 # optional - sage.rings.number_field
            0
            sage: edge.volume(measure='induced')                                # optional - sage.rings.number_field
            1

            sage: P = Polyhedron(backend='normaliz',vertices=[[1,0,0],[0,0,1],[-1,1,1],[-1,2,0]]) # optional - pynormaliz
            sage: P.volume()  # optional - pynormaliz
            0
            sage: P.volume(measure='induced')  # optional - pynormaliz          # optional - sage.rings.number_field
            2.598076211353316?
            sage: P.volume(measure='induced',engine='normaliz')  # optional - pynormaliz
            2.598076211353316
            sage: P.volume(measure='induced_rational')  # optional - pynormaliz, latte_int
            3/2
            sage: P.volume(measure='induced_rational',engine='normaliz')  # optional - pynormaliz
            3/2
            sage: P.volume(measure='induced_lattice')  # optional - pynormaliz
            3

        The same polytope without normaliz backend::

            sage: P = Polyhedron(vertices=[[1,0,0],[0,0,1],[-1,1,1],[-1,2,0]])
            sage: P.volume(measure='induced_lattice',engine='latte')  # optional - latte_int
            3

            sage: Dexact = polytopes.dodecahedron()                             # optional - sage.rings.number_field
            sage: v = Dexact.faces(2)[0].as_polyhedron().volume(measure='induced', engine='internal'); v   # optional - sage.rings.number_field
            1.53406271079097?
            sage: v = Dexact.faces(2)[4].as_polyhedron().volume(measure='induced', engine='internal'); v   # optional - sage.rings.number_field
            1.53406271079097?
            sage: RDF(v)    # abs tol 1e-9                                      # optional - sage.rings.number_field
            1.53406271079044

            sage: Dinexact = polytopes.dodecahedron(exact=False)
            sage: w = Dinexact.faces(2)[2].as_polyhedron().volume(measure='induced', engine='internal'); RDF(w) # abs tol 1e-9
            1.5340627082974878

            sage: [polytopes.simplex(d).volume(measure='induced') for d in range(1,5)] == [sqrt(d+1)/factorial(d) for d in range(1,5)]
            True

            sage: I = Polyhedron([[-3, 0], [0, 9]])
            sage: I.volume(measure='induced')                                   # optional - sage.rings.number_field
            9.48683298050514?
            sage: I.volume(measure='induced_rational') # optional -- latte_int
            3

            sage: T = Polyhedron([[3, 0, 0], [0, 4, 0], [0, 0, 5]])
            sage: T.volume(measure='induced')                                   # optional - sage.rings.number_field
            13.86542462386205?
            sage: T.volume(measure='induced_rational') # optional -- latte_int
            1/2

            sage: Q = Polyhedron(vertices=[(0, 0, 1, 1), (0, 1, 1, 0), (1, 1, 0, 0)])
            sage: Q.volume(measure='induced')
            1
            sage: Q.volume(measure='induced_rational') # optional -- latte_int
            1/2

        The volume of a full-dimensional unbounded polyhedron is infinity::

            sage: P = Polyhedron(vertices = [[1, 0], [0, 1]], rays = [[1, 1]])
            sage: P.volume()
            +Infinity

        The volume of a non full-dimensional unbounded polyhedron depends on the measure used::

            sage: P = Polyhedron(ieqs = [[1,1,1],[-1,-1,-1],[3,1,0]]); P
            A 1-dimensional polyhedron in QQ^2 defined as the convex hull of 1 vertex and 1 ray
            sage: P.volume()
            0
            sage: P.volume(measure='induced')
            +Infinity
            sage: P.volume(measure='ambient')
            0
            sage: P.volume(measure='induced_rational')  # optional - pynormaliz
            +Infinity
            sage: P.volume(measure='induced_rational',engine='latte')  # optional - latte_int
            +Infinity

        The volume in `0`-dimensional space is taken by counting measure::

            sage: P = Polyhedron(vertices=[[]]); P
            A 0-dimensional polyhedron in ZZ^0 defined as the convex hull of 1 vertex
            sage: P.volume()
            1
            sage: P = Polyhedron(vertices=[]); P
            The empty polyhedron in ZZ^0
            sage: P.volume()
            0

        TESTS:

        The cache of the volume is being pickled::

            sage: P = polytopes.cube()
            sage: P.volume()
            8
            sage: Q = loads(dumps(P))
            sage: Q.volume.is_in_cache()
            True
        """
        from sage.features import FeatureNotPresentError
        if measure == 'induced_rational' and engine not in ['auto', 'latte', 'normaliz']:
            raise RuntimeError("the induced rational measure can only be computed with the engine set to `auto`, `latte`, or `normaliz`")
        if measure == 'induced_lattice' and engine not in ['auto', 'latte', 'normaliz']:
            raise RuntimeError("the induced lattice measure can only be computed with the engine set to `auto`, `latte`, or `normaliz`")
        if engine == 'auto' and measure == 'induced_rational':
            # Enforce a default choice, change if a better engine is found.
            from sage.features.latte import Latte
            try:
                Latte().require()
                engine = 'latte'
            except FeatureNotPresentError:
                from sage.features.normaliz import PyNormaliz
                try:
                    PyNormaliz().require()
                    engine = 'normaliz'
                except FeatureNotPresentError:
                    raise RuntimeError("the induced rational measure can only be computed with the optional packages `latte_int`, or `pynormaliz`")

        if engine == 'auto' and measure == 'induced_lattice':
            # Enforce a default choice, change if a better engine is found.
            from sage.features.normaliz import PyNormaliz
            try:
                PyNormaliz().require()
                engine = 'normaliz'
            except FeatureNotPresentError:
                try:
                    from sage.features.latte import Latte
                    Latte().require()
                    engine = 'latte'
                except FeatureNotPresentError:
                    raise RuntimeError("the induced rational measure can only be computed with the optional packages `latte_int`, or `pynormaliz`")

        if engine == 'auto' and measure == 'ambient' and self.backend() == 'normaliz':
            engine = 'normaliz'

        if measure == 'ambient':
            if self.dim() < self.ambient_dim():
                return self.base_ring().zero()
            elif self.dim() == 0:
                return 1
            # if the polyhedron is unbounded, return infinity
            if not self.is_compact():
                from sage.rings.infinity import infinity
                return infinity
            if engine == 'lrs':
                return self._volume_lrs(**kwds)
            elif engine == 'latte':
                return self._volume_latte(**kwds)
            elif engine == 'normaliz':
                return self._volume_normaliz(measure='ambient')

            triangulation = self.triangulate(engine=engine, **kwds)
            pc = triangulation.point_configuration()
            return sum([pc.volume(simplex) for simplex in triangulation]) / ZZ(self.dim()).factorial()
        elif measure == 'induced':
            # if polyhedron is actually full-dimensional, return volume with ambient measure
            if self.dim() == self.ambient_dim():
                return self.volume(measure='ambient', engine=engine, **kwds)
            # if the polyhedron is unbounded, return infinity
            if not self.is_compact():
                from sage.rings.infinity import infinity
                return infinity
            if engine == 'normaliz':
                return self._volume_normaliz(measure='euclidean')
            # use an orthogonal transformation, which preserves volume up to a factor provided by the transformation matrix
            affine_hull_data = self.affine_hull_projection(orthogonal=True, as_polyhedron=True, as_affine_map=True)
            A = affine_hull_data.projection_linear_map.matrix()
            Adet = (A.transpose() * A).det()
            scaled_volume = affine_hull_data.image.volume(measure='ambient', engine=engine, **kwds)
            if Adet.is_square():
                sqrt_Adet = Adet.sqrt()
            else:
                sqrt_Adet = AA(Adet).sqrt()
                scaled_volume = AA(scaled_volume)
            return scaled_volume / sqrt_Adet
        elif measure == 'induced_rational':
            # if the polyhedron is unbounded, return infinity
            if not self.is_compact():
                from sage.rings.infinity import infinity
                return infinity
            if engine == 'latte':
                return self._volume_latte(**kwds)
            else:  # engine is 'normaliz'
                return self._volume_normaliz(measure='induced_lattice') / ZZ(self.dim()).factorial()
        elif measure == 'induced_lattice':
            # if the polyhedron is unbounded, return infinity
            if not self.is_compact():
                from sage.rings.infinity import infinity
                return infinity
            if engine == 'latte':
                return self._volume_latte(**kwds) * ZZ(self.dim()).factorial()
            else:  # engine is 'normaliz'
                return self._volume_normaliz(measure='induced_lattice')
        else:
            raise TypeError("the measure should be `ambient`, `induced`, `induced_rational`, or `induced_lattice`")

    def integrate(self, function, measure='ambient', **kwds):
        r"""
        Return the integral of ``function`` over this polytope.

        INPUT:

        - ``self`` -- Polyhedron

        - ``function`` -- a multivariate polynomial or
          a valid LattE description string for polynomials

        - ``measure`` -- string, the measure to use

          Allowed values are:

          * ``ambient`` (default): Lebesgue measure of ambient space,
          * ``induced``: Lebesgue measure of the affine hull,
          * ``induced_nonnormalized``: Lebesgue measure of the affine hull
            without the normalization by `\sqrt{\det(A^\top A)}` (with
            `A` being the affine transformation matrix; see :meth:`affine_hull`).

        - ``**kwds`` -- additional keyword arguments that
          are passed to the engine

        OUTPUT:

        The integral of the polynomial over the polytope

        .. NOTE::

            The polytope triangulation algorithm is used. This function depends
            on LattE (i.e., the ``latte_int`` optional package).

        EXAMPLES::

            sage: P = polytopes.cube()
            sage: x, y, z = polygens(QQ, 'x, y, z')
            sage: P.integrate(x^2*y^2*z^2)    # optional - latte_int
            8/27

        If the polyhedron has floating point coordinates, an inexact result can
        be obtained if we transform to rational coordinates::

            sage: P = 1.4142*polytopes.cube()
            sage: P_QQ = Polyhedron(vertices=[[QQ(vi) for vi in v] for v in P.vertex_generator()])
            sage: RDF(P_QQ.integrate(x^2*y^2*z^2))                  # optional - latte_int
            6.703841212195228

        Integral over a non full-dimensional polytope::

            sage: x, y = polygens(QQ, 'x, y')
            sage: P = Polyhedron(vertices=[[0,0],[1,1]])
            sage: P.integrate(x*y)    # optional - latte_int
            0
            sage: ixy = P.integrate(x*y, measure='induced'); ixy    # optional - latte_int
            0.4714045207910317?
            sage: ixy.parent()                                      # optional - latte_int
            Algebraic Real Field

        Convert to a symbolic expression::

            sage: ixy.radical_expression()                          # optional - latte_int
            1/3*sqrt(2)

        Another non full-dimensional polytope integration::

            sage: R.<x, y, z> = QQ[]
            sage: P = polytopes.simplex(2)
            sage: V = AA(P.volume(measure='induced')); V.radical_expression()
            1/2*sqrt(3)
            sage: P.integrate(R(1), measure='induced') == V                      # optional - latte_int
            True

        Computing the mass center::

            sage: (P.integrate(x, measure='induced') / V).radical_expression()   # optional - latte_int
            1/3
            sage: (P.integrate(y, measure='induced') / V).radical_expression()   # optional - latte_int
            1/3
            sage: (P.integrate(z, measure='induced') / V).radical_expression()   # optional - latte_int
            1/3

        TESTS:

        Testing a three-dimensional integral::

            sage: P = polytopes.octahedron()
            sage: x, y, z = polygens(QQ, 'x, y, z')
            sage: P.integrate(2*x^2*y^4*z^6+z^2)    # optional - latte_int
            630632/4729725

        Testing a polytope with non-rational vertices::

            sage: P = polytopes.icosahedron()                                   # optional - sage.rings.number_field
            sage: P.integrate(x^2*y^2*z^2)    # optional - latte_int            # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            TypeError: the base ring must be ZZ, QQ, or RDF

        Testing a univariate polynomial::

            sage: P = Polyhedron(vertices=[[0],[1]])
            sage: x = polygen(QQ, 'x')
            sage: P.integrate(x)    # optional - latte_int
            1/2

        Testing a polytope with floating point coordinates::

            sage: P = Polyhedron(vertices = [[0, 0], [1, 0], [1.1, 1.1], [0, 1]])
            sage: P.integrate('[[1,[2,2]]]')    # optional - latte_int
            Traceback (most recent call last):
            ...
            TypeError: LattE integrale cannot be applied over inexact rings

        Integration of zero-polynomial::

            sage: R.<x, y, z> = QQ[]
            sage: P = polytopes.simplex(2)
            sage: P.integrate(R(0))
            0
            sage: P.integrate('[]')  # with LattE description string
            0

        ::

            sage: R.<x, y, z> = QQ[]
            sage: P = Polyhedron(vertices=[(0, 0, 1), (0, 1, 0)])
            sage: P.integrate(x^2)
            0
        """
        if function == 0 or function == '[]':
            return self.base_ring().zero()

        if not self.is_compact():
            raise NotImplementedError(
                'integration over non-compact polyhedra not allowed')

        if measure == 'ambient':
            if not self.is_full_dimensional():
                return self.base_ring().zero()

            return self._integrate_latte_(function, **kwds)

        elif measure == 'induced' or measure == 'induced_nonnormalized':
            # if polyhedron is actually full-dimensional,
            # return with ambient measure
            if self.is_full_dimensional():
                return self.integrate(function, measure='ambient', **kwds)

            if isinstance(function, str):
                raise NotImplementedError(
                    'LattE description strings for polynomials not allowed '
                    'when using measure="induced"')

            # use an orthogonal transformation
            affine_hull_data = self.affine_hull_projection(orthogonal=True, return_all_data=True)
            polyhedron = affine_hull_data.image
            from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
            R = PolynomialRing(affine_hull_data.section_linear_map.base_ring(), 'x', self.dim())
            coordinate_images = affine_hull_data.section_linear_map.matrix().transpose() * vector(R.gens()) + affine_hull_data.section_translation

            hom = function.parent().hom(coordinate_images)
            function_in_affine_hull = hom(function)

            I = polyhedron.integrate(function_in_affine_hull,
                                     measure='ambient', **kwds)
            if measure == 'induced_nonnormalized':
                return I
            else:
                A = affine_hull_data.projection_linear_map.matrix()
                Adet = (A.transpose() * A).det()
                try:
                    Adet = AA.coerce(Adet)
                except TypeError:
                    pass
                return I / Adet.sqrt()

        else:
            raise ValueError('unknown measure "{}"'.format(measure))

    def _integrate_latte_(self, polynomial, **kwds):
        r"""
        Return the integral of a polynomial over this polytope by calling LattE.

        INPUT:

        - ``polynomial`` -- a multivariate polynomial or
          a valid LattE description string for polynomials

        - ``**kwds`` -- additional keyword arguments that are passed
          to the engine

        OUTPUT:

        The integral of the polynomial over the polytope.

        .. NOTE::

            The polytope triangulation algorithm is used. This function depends
            on LattE (i.e., the ``latte_int`` optional package).

        TESTS::

            sage: P = polytopes.cube()
            sage: x, y, z = polygens(QQ, 'x, y, z')
            sage: P._integrate_latte_(x^2 + y^2*z^2)    # optional - latte_int
            32/9

        ::

            sage: R = PolynomialRing(QQ, '', 0)
            sage: Polyhedron(vertices=[()]).integrate(R(42))
            42
        """
        from sage.interfaces.latte import integrate

        if self.base_ring() == RDF:
            raise TypeError("LattE integrale cannot be applied over inexact rings")
        if self.dimension() == 0:
            vertices = self.vertices()
            assert len(self.vertices()) == 1
            vertex = tuple(vertices[0])
            return polynomial(vertex)
        return integrate(self.cdd_Hrepresentation(),
                         polynomial,
                         cdd=True, **kwds)

    @cached_method
    def bounding_box(self, integral=False, integral_hull=False):
        r"""
        Return the coordinates of a rectangular box containing the non-empty polytope.

        INPUT:

        - ``integral`` -- Boolean (default: ``False``). Whether to
          only allow integral coordinates in the bounding box.

        - ``integral_hull`` -- Boolean (default: ``False``). If ``True``, return a
          box containing the integral points of the polytope, or ``None, None`` if it
          is known that the polytope has no integral points.

        OUTPUT:

        A pair of tuples ``(box_min, box_max)`` where ``box_min`` are
        the coordinates of a point bounding the coordinates of the
        polytope from below and ``box_max`` bounds the coordinates
        from above.

        EXAMPLES::

            sage: Polyhedron([ (1/3,2/3), (2/3, 1/3) ]).bounding_box()
            ((1/3, 1/3), (2/3, 2/3))
            sage: Polyhedron([ (1/3,2/3), (2/3, 1/3) ]).bounding_box(integral=True)
            ((0, 0), (1, 1))
            sage: Polyhedron([ (1/3,2/3), (2/3, 1/3) ]).bounding_box(integral_hull=True)
            (None, None)
            sage: Polyhedron([ (1/3,2/3), (3/3, 4/3) ]).bounding_box(integral_hull=True)
            ((1, 1), (1, 1))
            sage: polytopes.buckyball(exact=False).bounding_box()
            ((-0.8090169944, -0.8090169944, -0.8090169944), (0.8090169944, 0.8090169944, 0.8090169944))

        TESTS::

            sage: Polyhedron().bounding_box()
            Traceback (most recent call last):
            ...
            ValueError: empty polytope is not allowed
        """
        from sage.arith.misc import integer_ceil as ceil
        from sage.arith.misc import integer_floor as floor
        box_min = []
        box_max = []
        if not self.is_compact():
            raise ValueError("only polytopes (compact polyhedra) are allowed")
        if self.n_vertices() == 0:
            raise ValueError("empty polytope is not allowed")
        for i in range(self.ambient_dim()):
            coords = [v[i] for v in self.vertex_generator()]
            max_coord = max(coords)
            min_coord = min(coords)
            if integral_hull:
                a = ceil(min_coord)
                b = floor(max_coord)
                if a > b:
                    return None, None
                box_max.append(b)
                box_min.append(a)
            elif integral:
                box_max.append(ceil(max_coord))
                box_min.append(floor(min_coord))
            else:
                box_max.append(max_coord)
                box_min.append(min_coord)
        return (tuple(box_min), tuple(box_max))

    def affine_hull(self, *args, **kwds):
        r"""
        Return the affine hull of ``self`` as a polyhedron.

        EXAMPLES::

            sage: half_plane_in_space = Polyhedron(ieqs=[(0,1,0,0)], eqns=[(0,0,0,1)])
            sage: half_plane_in_space.affine_hull().Hrepresentation()
            (An equation (0, 0, 1) x + 0 == 0,)

            sage: polytopes.cube().affine_hull().is_universe()
            True
        """
        if args or kwds:
            raise TypeError("the method 'affine_hull' does not take any parameters; perhaps you meant 'affine_hull_projection'")
        if not self.inequalities():
            return self
        self_as_face = self.faces(self.dimension())[0]
        return self_as_face.affine_tangent_cone()

    @cached_method
    def _affine_hull_projection(self, *,
                                as_convex_set=True, as_affine_map=True, as_section_map=True,
                                orthogonal=False, orthonormal=False,
                                extend=False, minimal=False):
        r"""
        Return ``self`` projected into its affine hull.

        INPUT:

        See :meth:`affine_hull_projection`.

        OUTPUT:

        An instance of :class:`~sage.geometry.convex_set.AffineHullProjectionData`.
        See :meth:`affine_hull_projection` for details.

        TESTS:

        Check that :trac:`23355` is fixed::

            sage: P = Polyhedron([[7]]); P
            A 0-dimensional polyhedron in ZZ^1 defined as the convex hull of 1 vertex
            sage: P.affine_hull_projection()
            A 0-dimensional polyhedron in ZZ^0 defined as the convex hull of 1 vertex
            sage: P.affine_hull_projection(orthonormal='True')
            A 0-dimensional polyhedron in QQ^0 defined as the convex hull of 1 vertex
            sage: P.affine_hull_projection(orthogonal='True')
            A 0-dimensional polyhedron in QQ^0 defined as the convex hull of 1 vertex

        Check that :trac:`24047` is fixed::

            sage: P1 = Polyhedron(vertices=([[-1, 1], [0, -1], [0, 0], [-1, -1]]))
            sage: P2 = Polyhedron(vertices=[[1, 1], [1, -1], [0, -1], [0, 0]])
            sage: P = P1.intersection(P2)
            sage: A, b = P.affine_hull_projection(as_affine_map=True, orthonormal=True, extend=True)  # optional - sage.rings.number_field

            sage: Polyhedron([(2,3,4)]).affine_hull_projection()
            A 0-dimensional polyhedron in ZZ^0 defined as the convex hull of 1 vertex

        Check that backend is preserved::

            sage: polytopes.simplex(backend='field').affine_hull_projection().backend()
            'field'

            sage: P = Polyhedron(vertices=[[0,0], [1,0]], backend='field')
            sage: P.affine_hull_projection(orthogonal=True, orthonormal=True, extend=True).backend()  # optional - sage.rings.number_field
            'field'

        Check that :trac:`29116` is fixed::

            sage: V =[
            ....:    [1, 0, -1, 0, 0],
            ....:    [1, 0, 0, -1, 0],
            ....:    [1, 0, 0, 0, -1],
            ....:    [1, 0, 0, +1, 0],
            ....:    [1, 0, 0, 0, +1],
            ....:    [1, +1, 0, 0, 0]
            ....:     ]
            sage: P = Polyhedron(V)
            sage: P.affine_hull_projection()
            A 4-dimensional polyhedron in ZZ^4 defined as the convex hull of 6 vertices
            sage: P.affine_hull_projection(orthonormal=True)
            Traceback (most recent call last):
            ...
            ValueError: the base ring needs to be extended; try with "extend=True"
            sage: P.affine_hull_projection(orthonormal=True, extend=True)                             # optional - sage.rings.number_field
            A 4-dimensional polyhedron in AA^4 defined as the convex hull of 6 vertices
        """
        result = AffineHullProjectionData()

        if self.is_empty():
            raise ValueError('affine hull projection of an empty polyhedron is undefined')

        # handle trivial full-dimensional case
        if self.ambient_dim() == self.dim():
            if as_convex_set:
                result.image = self
            if as_affine_map:
                identity = linear_transformation(matrix(self.base_ring(),
                                                        self.dim(),
                                                        self.dim(),
                                                        self.base_ring().one()))
                result.projection_linear_map = result.section_linear_map = identity
                result.projection_translation = result.section_translation = self.ambient_space().zero()
        elif orthogonal or orthonormal:
            # see TODO
            if not self.is_compact():
                raise NotImplementedError('"orthogonal=True" and "orthonormal=True" work only for compact polyhedra')
            affine_basis = self.an_affine_basis()
            v0 = affine_basis[0].vector()
            # We implicitly translate the first vertex of the affine basis to zero.
            vi = tuple(v.vector() - v0 for v in affine_basis[1:])
            M = matrix(self.base_ring(), self.dim(), self.ambient_dim(), vi)

            # Switch base_ring to AA if necessary,
            # since gram_schmidt needs to be able to take square roots.
            # Pick orthonormal basis and transform all vertices accordingly
            # if the orthonormal transform makes it necessary, change base ring.
            try:
                A, G = M.gram_schmidt(orthonormal=orthonormal)
            except TypeError:
                if not extend:
                    raise ValueError('the base ring needs to be extended; try with "extend=True"')
                M = matrix(AA, M)
                A = M.gram_schmidt(orthonormal=orthonormal)[0]
                if minimal:
                    from sage.rings.qqbar import number_field_elements_from_algebraics
                    new_ring = number_field_elements_from_algebraics(A.list(), embedded=True, minimal=True)[0]
                    A = A.change_ring(new_ring)
            L = linear_transformation(A, side='right')
            ambient_translation = -vector(A.base_ring(), affine_basis[0])
            image_translation = A * ambient_translation
            # Note the order. We compute ``A*self`` and then translate the image.
            # ``A*self`` uses the incidence matrix and we avoid recomputation.
            # Also, if the new base ring is ``AA``, we want to avoid computing the incidence matrix in that ring.
            # ``convert=True`` takes care of the case, where there might be no coercion (``AA`` and quadratic field).
            if as_convex_set:
                result.image = self.linear_transformation(A, new_base_ring=A.base_ring()) + image_translation
            if as_affine_map:
                result.projection_linear_map = L
                result.projection_translation = image_translation
            if as_section_map:
                L_dagger = linear_transformation(A.transpose() * (A * A.transpose()).inverse(), side='right')
                result.section_linear_map = L_dagger
                result.section_translation = v0.change_ring(A.base_ring())
        else:
            # translate one vertex to the origin
            v0 = self.vertices()[0].vector()
            gens = []
            for v in self.vertices()[1:]:
                gens.append(v.vector() - v0)
            for r in self.rays():
                gens.append(r.vector())
            for l in self.lines():
                gens.append(l.vector())

            # Pick subset of coordinates to coordinatize the affine span
            M = matrix(gens)
            pivots = M.pivots()

            A = matrix(self.base_ring(), len(pivots), self.ambient_dim(),
                       [[1 if j == i else 0 for j in range(self.ambient_dim())] for i in pivots])
            if as_affine_map:
                image_translation = vector(self.base_ring(), self.dim())
                L = linear_transformation(A, side='right')
                result.projection_linear_map = L
                result.projection_translation = image_translation
            if as_convex_set:
                result.image = A*self
            if as_section_map:
                if self.dim():
                    B = M.transpose()/(A*M.transpose())
                else:
                    B = matrix(self.ambient_dim(), 0)
                L_section = linear_transformation(B, side='right')
                result.section_linear_map = L_section
                result.section_translation = v0 - L_section(L(v0) + image_translation)

        return result

    def affine_hull_projection(self,
                               as_polyhedron=None, as_affine_map=False,
                               orthogonal=False, orthonormal=False,
                               extend=False, minimal=False,
                               return_all_data=False,
                               *, as_convex_set=None):
        r"""Return the polyhedron projected into its affine hull.

        Each polyhedron is contained in some smallest affine subspace
        (possibly the entire ambient space) -- its affine hull.  We
        provide an affine linear map that projects the ambient space of
        the polyhedron to the standard Euclidean space of dimension of
        the polyhedron, which restricts to a bijection from the affine
        hull.

        The projection map is not unique; some parameters control the
        choice of the map.  Other parameters control the output of the
        function.

        INPUT:

        - ``as_polyhedron`` (or ``as_convex_set``) -- (boolean or the default
          ``None``) and

        - ``as_affine_map`` -- (boolean, default ``False``) control the output

          The default ``as_polyhedron=None`` translates to
          ``as_polyhedron=not as_affine_map``,
          therefore to ``as_polyhedron=True`` if nothing is specified.

          If exactly one of either ``as_polyhedron`` or ``as_affine_map`` is
          set, then either a polyhedron or the affine transformation
          is returned. The affine transformation
          sends the embedded polytope to a fulldimensional one.
          It is given as a pair ``(A, b)``, where A is a linear transformation
          and `b` is a vector, and the affine transformation sends ``v`` to
          ``A(v)+b``.

          If both ``as_polyhedron`` and ``as_affine_map`` are set, then
          both are returned, encapsulated in an instance of
          :class:`~sage.geometry.convex_set.AffineHullProjectionData`.

        - ``return_all_data`` -- (boolean, default ``False``)

          If set, then ``as_polyhedron`` and ``as_affine_map`` will set
          (possibly overridden) and additional (internal) data concerning
          the transformation is returned. Everything is encapsulated
          in an instance of
          :class:`~sage.geometry.convex_set.AffineHullProjectionData` in
          this case.

        - ``orthogonal`` -- boolean (default: ``False``); if ``True``,
          provide an orthogonal transformation.

        - ``orthonormal`` -- boolean (default: ``False``); if ``True``,
          provide an orthonormal transformation. If the base ring does not
          provide the necessary square roots, the extend parameter
          needs to be set to ``True``.

        - ``extend`` -- boolean (default: ``False``); if ``True``,
          allow base ring to be extended if necessary. This becomes
          relevant when requiring an orthonormal transformation.

        - ``minimal`` -- boolean (default: ``False``); if ``True``,
          when doing an extension, it computes the minimal base ring of the
          extension, otherwise the base ring is ``AA``.

        OUTPUT:

        A full-dimensional polyhedron or an affine transformation,
        depending on the parameters ``as_polyhedron`` and ``as_affine_map``,
        or an instance of :class:`~sage.geometry.convex_set.AffineHullProjectionData`
        containing all data (parameter ``return_all_data``).

        If the output is an instance of
        :class:`~sage.geometry.convex_set.AffineHullProjectionData`, the
        following fields may be set:

        - ``image`` -- the projection of the original polyhedron

        - ``projection_map`` -- the affine map as a pair whose first component
          is a linear transformation and its second component a shift;
          see above.

        - ``section_map`` -- an affine map as a pair whose first component
          is a linear transformation and its second component a shift.
          It maps the codomain of ``affine_map`` to the affine hull of
          ``self``.  It is a right inverse of ``projection_map``.

        Note that all of these data are compatible.

         .. TODO::

            - make the parameters ``orthogonal`` and ``orthonormal`` work
              with unbounded polyhedra.

        EXAMPLES::

            sage: triangle = Polyhedron([(1,0,0), (0,1,0), (0,0,1)]);  triangle
            A 2-dimensional polyhedron in ZZ^3 defined as the convex hull of 3 vertices
            sage: triangle.affine_hull_projection()
            A 2-dimensional polyhedron in ZZ^2 defined as the convex hull of 3 vertices

            sage: half3d = Polyhedron(vertices=[(3,2,1)], rays=[(1,0,0)])
            sage: half3d.affine_hull_projection().Vrepresentation()
            (A ray in the direction (1), A vertex at (3))

        The resulting affine hulls depend on the parameter ``orthogonal`` and ``orthonormal``::

            sage: L = Polyhedron([[1,0],[0,1]]); L
            A 1-dimensional polyhedron in ZZ^2 defined as the convex hull of 2 vertices
            sage: A = L.affine_hull_projection(); A
            A 1-dimensional polyhedron in ZZ^1 defined as the convex hull of 2 vertices
            sage: A.vertices()
            (A vertex at (0), A vertex at (1))
            sage: A = L.affine_hull_projection(orthogonal=True); A
            A 1-dimensional polyhedron in QQ^1 defined as the convex hull of 2 vertices
            sage: A.vertices()
            (A vertex at (0), A vertex at (2))
            sage: A = L.affine_hull_projection(orthonormal=True)                                  # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            ValueError: the base ring needs to be extended; try with "extend=True"
            sage: A = L.affine_hull_projection(orthonormal=True, extend=True); A                  # optional - sage.rings.number_field
            A 1-dimensional polyhedron in AA^1 defined as the convex hull of 2 vertices
            sage: A.vertices()                                                                    # optional - sage.rings.number_field
            (A vertex at (1.414213562373095?), A vertex at (0.?e-18))

        More generally::

            sage: S = polytopes.simplex(); S
            A 3-dimensional polyhedron in ZZ^4 defined as the convex hull of 4 vertices
            sage: S.vertices()
            (A vertex at (0, 0, 0, 1),
             A vertex at (0, 0, 1, 0),
             A vertex at (0, 1, 0, 0),
             A vertex at (1, 0, 0, 0))
            sage: A = S.affine_hull_projection(); A
            A 3-dimensional polyhedron in ZZ^3 defined as the convex hull of 4 vertices
            sage: A.vertices()
            (A vertex at (0, 0, 0),
             A vertex at (0, 0, 1),
             A vertex at (0, 1, 0),
             A vertex at (1, 0, 0))
            sage: A = S.affine_hull_projection(orthogonal=True); A
            A 3-dimensional polyhedron in QQ^3 defined as the convex hull of 4 vertices
            sage: A.vertices()
            (A vertex at (0, 0, 0),
             A vertex at (2, 0, 0),
             A vertex at (1, 3/2, 0),
             A vertex at (1, 1/2, 4/3))
            sage: A = S.affine_hull_projection(orthonormal=True, extend=True); A
            A 3-dimensional polyhedron in AA^3 defined as the convex hull of 4 vertices
            sage: A.vertices()
            (A vertex at (0.7071067811865475?, 0.4082482904638630?, 1.154700538379252?),
             A vertex at (0.7071067811865475?, 1.224744871391589?, 0.?e-18),
             A vertex at (1.414213562373095?, 0.?e-18, 0.?e-18),
             A vertex at (0.?e-18, 0.?e-18, 0.?e-18))

        With the parameter ``minimal`` one can get a minimal base ring::

            sage: s = polytopes.simplex(3)
            sage: s_AA = s.affine_hull_projection(orthonormal=True, extend=True)
            sage: s_AA.base_ring()
            Algebraic Real Field
            sage: s_full = s.affine_hull_projection(orthonormal=True, extend=True, minimal=True)
            sage: s_full.base_ring()
            Number Field in a with defining polynomial y^4 - 4*y^2 + 1 with a = 0.5176380902050415?

        More examples with the ``orthonormal`` parameter::

            sage: P = polytopes.permutahedron(3); P                   # optional - sage.combinat  # optional - sage.rings.number_field
            A 2-dimensional polyhedron in ZZ^3 defined as the convex hull of 6 vertices
            sage: set([F.as_polyhedron().affine_hull_projection(orthonormal=True, extend=True).volume() for F in P.affine_hull_projection().faces(1)]) == {1, sqrt(AA(2))}  # optional - sage.combinat  # optional - sage.rings.number_field
            True
            sage: set([F.as_polyhedron().affine_hull_projection(orthonormal=True, extend=True).volume() for F in P.affine_hull_projection(orthonormal=True, extend=True).faces(1)]) == {sqrt(AA(2))}  # optional - sage.combinat  # optional - sage.rings.number_field
            True

            sage: D = polytopes.dodecahedron()                                                    # optional - sage.rings.number_field
            sage: F = D.faces(2)[0].as_polyhedron()                                               # optional - sage.rings.number_field
            sage: F.affine_hull_projection(orthogonal=True)                                       # optional - sage.rings.number_field
            A 2-dimensional polyhedron in (Number Field in sqrt5 with defining polynomial x^2 - 5 with sqrt5 = 2.236067977499790?)^2 defined as the convex hull of 5 vertices
            sage: F.affine_hull_projection(orthonormal=True, extend=True)                         # optional - sage.rings.number_field
            A 2-dimensional polyhedron in AA^2 defined as the convex hull of 5 vertices

            sage: K.<sqrt2> = QuadraticField(2)                                                   # optional - sage.rings.number_field
            sage: P = Polyhedron([2*[K.zero()],2*[sqrt2]]); P                                     # optional - sage.rings.number_field
            A 1-dimensional polyhedron in (Number Field in sqrt2 with defining polynomial x^2 - 2 with sqrt2 = 1.414213562373095?)^2 defined as the convex hull of 2 vertices
            sage: P.vertices()                                                                    # optional - sage.rings.number_field
            (A vertex at (0, 0), A vertex at (sqrt2, sqrt2))
            sage: A = P.affine_hull_projection(orthonormal=True); A                               # optional - sage.rings.number_field
            A 1-dimensional polyhedron in (Number Field in sqrt2 with defining polynomial x^2 - 2 with sqrt2 = 1.414213562373095?)^1 defined as the convex hull of 2 vertices
            sage: A.vertices()                                                                    # optional - sage.rings.number_field
            (A vertex at (0), A vertex at (2))

            sage: K.<sqrt3> = QuadraticField(3)                                                   # optional - sage.rings.number_field
            sage: P = Polyhedron([2*[K.zero()],2*[sqrt3]]); P                                     # optional - sage.rings.number_field
            A 1-dimensional polyhedron in (Number Field in sqrt3 with defining polynomial x^2 - 3 with sqrt3 = 1.732050807568878?)^2 defined as the convex hull of 2 vertices
            sage: P.vertices()                                                                    # optional - sage.rings.number_field
            (A vertex at (0, 0), A vertex at (sqrt3, sqrt3))
            sage: A = P.affine_hull_projection(orthonormal=True)                                  # optional - sage.rings.number_field
            Traceback (most recent call last):
            ...
            ValueError: the base ring needs to be extended; try with "extend=True"
            sage: A = P.affine_hull_projection(orthonormal=True, extend=True); A                  # optional - sage.rings.number_field
            A 1-dimensional polyhedron in AA^1 defined as the convex hull of 2 vertices
            sage: A.vertices()                                                                    # optional - sage.rings.number_field
            (A vertex at (0), A vertex at (2.449489742783178?))
            sage: sqrt(6).n()                                                                     # optional - sage.rings.number_field
            2.44948974278318

        The affine hull is combinatorially equivalent to the input::

            sage: P.is_combinatorially_isomorphic(P.affine_hull_projection())                     # optional - sage.rings.number_field
            True
            sage: P.is_combinatorially_isomorphic(P.affine_hull_projection(orthogonal=True))      # optional - sage.rings.number_field
            True
            sage: P.is_combinatorially_isomorphic(P.affine_hull_projection(orthonormal=True, extend=True))   # optional - sage.rings.number_field
            True

        The ``orthonormal=True`` parameter preserves volumes;
        it provides an isometric copy of the polyhedron::

            sage: Pentagon = polytopes.dodecahedron().faces(2)[0].as_polyhedron()                 # optional - sage.rings.number_field
            sage: P = Pentagon.affine_hull_projection(orthonormal=True, extend=True)              # optional - sage.rings.number_field
            sage: _, c= P.is_inscribed(certificate=True)                                          # optional - sage.rings.number_field
            sage: c                                                                               # optional - sage.rings.number_field
            (0.4721359549995794?, 0.6498393924658126?)
            sage: circumradius = (c-vector(P.vertices()[0])).norm()                               # optional - sage.rings.number_field
            sage: p = polytopes.regular_polygon(5)                                                # optional - sage.rings.number_field
            sage: p.volume()                                                                      # optional - sage.rings.number_field
            2.377641290737884?
            sage: P.volume()                                                                      # optional - sage.rings.number_field
            1.53406271079097?
            sage: p.volume()*circumradius^2                                                       # optional - sage.rings.number_field
            1.534062710790965?
            sage: P.volume() == p.volume()*circumradius^2                                         # optional - sage.rings.number_field
            True

        One can also use ``orthogonal`` parameter to calculate volumes;
        in this case we don't need to switch base rings. One has to divide
        by the square root of the determinant of the linear part of the
        affine transformation times its transpose::

            sage: Pentagon = polytopes.dodecahedron().faces(2)[0].as_polyhedron()                 # optional - sage.rings.number_field
            sage: Pnormal = Pentagon.affine_hull_projection(orthonormal=True, extend=True)        # optional - sage.rings.number_field
            sage: Pgonal = Pentagon.affine_hull_projection(orthogonal=True)                       # optional - sage.rings.number_field
            sage: A, b = Pentagon.affine_hull_projection(orthogonal=True, as_affine_map=True)     # optional - sage.rings.number_field
            sage: Adet = (A.matrix().transpose()*A.matrix()).det()                                # optional - sage.rings.number_field
            sage: Pnormal.volume()                                                                # optional - sage.rings.number_field
            1.53406271079097?
            sage: Pgonal.volume()/Adet.sqrt(extend=True)                                          # optional - sage.rings.number_field
            -80*(55*sqrt(5) - 123)/sqrt(-6368*sqrt(5) + 14240)
            sage: Pgonal.volume()/AA(Adet).sqrt().n(digits=20)                                    # optional - sage.rings.number_field
            1.5340627107909646813
            sage: AA(Pgonal.volume()^2) == (Pnormal.volume()^2)*AA(Adet)                          # optional - sage.rings.number_field
            True

        Another example with ``as_affine_map=True``::

            sage: P = polytopes.permutahedron(4)                                                      # optional - sage.combinat  # optional - sage.rings.number_field
            sage: A, b = P.affine_hull_projection(orthonormal=True, as_affine_map=True, extend=True)  # optional - sage.combinat  # optional - sage.rings.number_field
            sage: Q = P.affine_hull_projection(orthonormal=True, extend=True)                         # optional - sage.combinat  # optional - sage.rings.number_field
            sage: Q.center()                                                                          # optional - sage.combinat  # optional - sage.rings.number_field
            (0.7071067811865475?, 1.224744871391589?, 1.732050807568878?)
            sage: A(P.center()) + b == Q.center()                                                     # optional - sage.combinat  # optional - sage.rings.number_field
            True

        For unbounded, non full-dimensional polyhedra, the ``orthogonal=True`` and ``orthonormal=True``
        is not implemented::

            sage: P = Polyhedron(ieqs=[[0, 1, 0], [0, 0, 1], [0, 0, -1]]); P
            A 1-dimensional polyhedron in QQ^2 defined as the convex hull of 1 vertex and 1 ray
            sage: P.is_compact()
            False
            sage: P.is_full_dimensional()
            False
            sage: P.affine_hull_projection(orthogonal=True)
            Traceback (most recent call last):
            ...
            NotImplementedError: "orthogonal=True" and "orthonormal=True" work only for compact polyhedra
            sage: P.affine_hull_projection(orthonormal=True)
            Traceback (most recent call last):
            ...
            NotImplementedError: "orthogonal=True" and "orthonormal=True" work only for compact polyhedra

        Setting ``as_affine_map`` to ``True``
        without ``orthogonal`` or ``orthonormal`` set to ``True``::

            sage: S = polytopes.simplex()
            sage: S.affine_hull_projection(as_affine_map=True)
            (Vector space morphism represented by the matrix:
             [1 0 0]
             [0 1 0]
             [0 0 1]
             [0 0 0]
             Domain: Vector space of dimension 4 over Rational Field
             Codomain: Vector space of dimension 3 over Rational Field,
             (0, 0, 0))

        If the polyhedron is full-dimensional, it is returned::

            sage: polytopes.cube().affine_hull_projection()
            A 3-dimensional polyhedron in ZZ^3 defined as the convex hull of 8 vertices
            sage: polytopes.cube().affine_hull_projection(as_affine_map=True)
            (Vector space morphism represented by the matrix:
             [1 0 0]
             [0 1 0]
             [0 0 1]
             Domain: Vector space of dimension 3 over Rational Field
             Codomain: Vector space of dimension 3 over Rational Field,
             (0, 0, 0))

        Return polyhedron and affine map::

            sage: S = polytopes.simplex(2)
            sage: data = S.affine_hull_projection(orthogonal=True,
            ....:                                 as_polyhedron=True,
            ....:                                 as_affine_map=True); data
            AffineHullProjectionData(image=A 2-dimensional polyhedron in QQ^2
                    defined as the convex hull of 3 vertices,
                projection_linear_map=Vector space morphism represented by the matrix:
                    [  -1 -1/2]
                    [   1 -1/2]
                    [   0    1]
                    Domain: Vector space of dimension 3 over Rational Field
                    Codomain: Vector space of dimension 2 over Rational Field,
                projection_translation=(1, 1/2),
                section_linear_map=None,
                section_translation=None)

        Return all data::

            sage: data = S.affine_hull_projection(orthogonal=True, return_all_data=True); data
            AffineHullProjectionData(image=A 2-dimensional polyhedron in QQ^2
                    defined as the convex hull of 3 vertices,
                projection_linear_map=Vector space morphism represented by the matrix:
                    [  -1 -1/2]
                    [   1 -1/2]
                    [   0    1]
                    Domain: Vector space of dimension 3 over Rational Field
                    Codomain: Vector space of dimension 2 over Rational Field,
                projection_translation=(1, 1/2),
                section_linear_map=Vector space morphism represented by the matrix:
                    [-1/2  1/2    0]
                    [-1/3 -1/3  2/3]
                    Domain: Vector space of dimension 2 over Rational Field
                    Codomain: Vector space of dimension 3 over Rational Field, section_translation=(1, 0, 0))

        The section map is a right inverse of the projection map::

            sage: data.image.linear_transformation(data.section_linear_map.matrix().transpose()) + data.section_translation == S
            True

        Same without ``orthogonal=True``::

            sage: data = S.affine_hull_projection(return_all_data=True); data
            AffineHullProjectionData(image=A 2-dimensional polyhedron in ZZ^2
                    defined as the convex hull of 3 vertices,
                projection_linear_map=Vector space morphism represented by the matrix:
                    [1 0]
                    [0 1]
                    [0 0]
                    Domain: Vector space of dimension 3 over Rational Field
                    Codomain: Vector space of dimension 2 over Rational Field, projection_translation=(0, 0),
                section_linear_map=Vector space morphism represented by the matrix:
                    [ 1  0 -1]
                    [ 0  1 -1]
                    Domain: Vector space of dimension 2 over Rational Field
                    Codomain: Vector space of dimension 3 over Rational Field, section_translation=(0, 0, 1))
            sage: data.image.linear_transformation(data.section_linear_map.matrix().transpose()) + data.section_translation == S
            True

        ::

            sage: P0 = Polyhedron(
            ....:     ieqs=[(0, -1, 0, 1, 1, 1), (0, 1, 1, 0, -1, -1), (0, -1, 1, 1, 0, 0),
            ....:           (0, 1, 0, 0, 0, 0), (0, 0, 1, 1, -1, -1), (0, 0, 0, 0, 0, 1),
            ....:           (0, 0, 0, 0, 1, 0), (0, 0, 0, 1, 0, -1), (0, 0, 1, 0, 0, 0)])
            sage: P = P0.intersection(Polyhedron(eqns=[(-1, 1, 1, 1, 1, 1)]))
            sage: P.dim()
            4
            sage: P.affine_hull_projection(orthogonal=True, as_affine_map=True)[0]
            Vector space morphism represented by the matrix:
            [    0     0     0   1/3]
            [ -2/3  -1/6     0 -1/12]
            [  1/3  -1/6   1/2 -1/12]
            [    0   1/2     0 -1/12]
            [  1/3  -1/6  -1/2 -1/12]
            Domain: Vector space of dimension 5 over Rational Field
            Codomain: Vector space of dimension 4 over Rational Field
        """
        if as_polyhedron is not None:
            as_convex_set = as_polyhedron
        return super().affine_hull_projection(
            as_convex_set=as_convex_set, as_affine_map=as_affine_map,
            orthogonal=orthogonal, orthonormal=orthonormal,
            extend=extend, minimal=minimal,
            return_all_data=return_all_data)

    def _test_affine_hull_projection(self, tester=None, verbose=False, **options):
        """
        Run tests on the method :meth:`.affine_hull_projection`.

        TESTS::

            sage: D = polytopes.dodecahedron()                                  # optional - sage.rings.number_field
            sage: D.facets()[0].as_polyhedron()._test_affine_hull_projection()  # optional - sage.rings.number_field
        """
        if tester is None:
            tester = self._tester(**options)

        if self.is_empty():
            # Undefined, nothing to test
            return

        if self.n_vertices() > 30 or self.n_facets() > 30 or self.dim() > 6:
            # Avoid very long doctests.
            return

        data_sets = [None]*4
        data_sets[0] = self.affine_hull_projection(return_all_data=True)
        if self.is_compact():
            data_sets[1] = self.affine_hull_projection(return_all_data=True,
                                                       orthogonal=True,
                                                       extend=True)
            data_sets[2] = self.affine_hull_projection(return_all_data=True,
                                                       orthonormal=True,
                                                       extend=True)
            data_sets[3] = self.affine_hull_projection(return_all_data=True,
                                                       orthonormal=True,
                                                       extend=True,
                                                       minimal=True)
        else:
            data_sets = data_sets[:1]

        for i, data in enumerate(data_sets):
            if verbose:
                print("Running test number {}".format(i))
            M = data.projection_linear_map.matrix().transpose()
            tester.assertEqual(self.linear_transformation(M, new_base_ring=M.base_ring())
                               + data.projection_translation,
                               data.image)

            M = data.section_linear_map.matrix().transpose()
            if M.base_ring() is AA:
                self_extend = self.change_ring(AA)
            else:
                self_extend = self
            tester.assertEqual(data.image.linear_transformation(M)
                               + data.section_translation,
                               self_extend)
            if i == 0:
                tester.assertEqual(data.image.base_ring(), self.base_ring())
            else:
                # Test whether the map is orthogonal.
                M = data.projection_linear_map.matrix()
                tester.assertTrue((M.transpose() * M).is_diagonal())
                if i > 1:
                    # Test whether the map is orthonormal.
                    tester.assertTrue((M.transpose() * M).is_one())
            if i == 3:
                # Test that the extension is indeed minimal.
                if self.base_ring() is not AA:
                    tester.assertIsNot(data.image.base_ring(), AA)

    def affine_hull_manifold(self, name=None, latex_name=None, start_index=0, ambient_space=None,
                             ambient_chart=None, names=None, **kwds):
        r"""
        Return the affine hull of ``self`` as a manifold.

        If ``self`` is full-dimensional, it is just the ambient Euclidean space.
        Otherwise, it is a Riemannian submanifold of the ambient Euclidean space.

        INPUT:

        - ``ambient_space`` -- a :class:`~sage.manifolds.differentiable.examples.euclidean.EuclideanSpace`
          of the ambient dimension (default: the manifold of ``ambient_chart``, if provided;
          otherwise, a new instance of ``EuclideanSpace``).

        - ``ambient_chart`` -- a chart on ``ambient_space``.

        - ``names`` -- names for the coordinates on the affine hull.

        - optional arguments accepted by :meth:`affine_hull_projection`.

        The default chart is determined by the optional arguments of
        :meth:`affine_hull_projection`.

        EXAMPLES::

            sage: triangle = Polyhedron([(1,0,0), (0,1,0), (0,0,1)]);  triangle
            A 2-dimensional polyhedron in ZZ^3 defined as the convex hull of 3 vertices
            sage: A = triangle.affine_hull_manifold(name='A'); A
            2-dimensional Riemannian submanifold A embedded in the Euclidean space E^3
            sage: A.embedding().display()
            A → E^3
               (x0, x1) ↦ (x, y, z) = (t0 + x0, t0 + x1, t0 - x0 - x1 + 1)
            sage: A.embedding().inverse().display()
            E^3 → A
               (x, y, z) ↦ (x0, x1) = (x, y)
            sage: A.adapted_chart()
            [Chart (E^3, (x0_E3, x1_E3, t0_E3))]
            sage: A.normal().display()
            n = 1/3*sqrt(3) e_x + 1/3*sqrt(3) e_y + 1/3*sqrt(3) e_z
            sage: A.induced_metric()       # Need to call this before volume_form
            Riemannian metric gamma on the 2-dimensional Riemannian submanifold A embedded in the Euclidean space E^3
            sage: A.volume_form()
            2-form eps_gamma on the 2-dimensional Riemannian submanifold A embedded in the Euclidean space E^3

        Orthogonal version::

            sage: A = triangle.affine_hull_manifold(name='A', orthogonal=True); A
            2-dimensional Riemannian submanifold A embedded in the Euclidean space E^3
            sage: A.embedding().display()
            A → E^3
               (x0, x1) ↦ (x, y, z) = (t0 - 1/2*x0 - 1/3*x1 + 1, t0 + 1/2*x0 - 1/3*x1, t0 + 2/3*x1)
            sage: A.embedding().inverse().display()
            E^3 → A
               (x, y, z) ↦ (x0, x1) = (-x + y + 1, -1/2*x - 1/2*y + z + 1/2)

        Arrangement of affine hull of facets::

            sage: D = polytopes.dodecahedron()                                  # optional - sage.rings.number_field
            sage: E3 = EuclideanSpace(3)                                        # optional - sage.rings.number_field
            sage: submanifolds = [                                              # optional - sage.rings.number_field
            ....:     F.as_polyhedron().affine_hull_manifold(name=f'F{i}', orthogonal=True, ambient_space=E3)
            ....:     for i, F in enumerate(D.facets())]
            sage: sum(FM.plot({}, srange(-2, 2, 0.1), srange(-2, 2, 0.1), opacity=0.2)  # not tested  # optional - sage.plot  # optional - sage.rings.number_field
            ....:     for FM in submanifolds) + D.plot()
            Graphics3d Object

        Full-dimensional case::

            sage: cube = polytopes.cube(); cube
            A 3-dimensional polyhedron in ZZ^3 defined as the convex hull of 8 vertices
            sage: cube.affine_hull_manifold()
            Euclidean space E^3

        """
        if ambient_space is None:
            if ambient_chart is not None:
                ambient_space = ambient_chart.manifold()
            else:
                from sage.manifolds.differentiable.examples.euclidean import EuclideanSpace
                ambient_space = EuclideanSpace(self.ambient_dim(), start_index=start_index)
        if ambient_space.dimension() != self.ambient_dim():
            raise ValueError('ambient_space and ambient_chart must match the ambient dimension')

        if self.is_full_dimensional():
            return ambient_space

        if ambient_chart is None:
            ambient_chart = ambient_space.default_chart()
        CE = ambient_chart

        from sage.manifolds.manifold import Manifold
        if name is None:
            name, latex_name = self._affine_hull_name_latex_name()
        H = Manifold(self.dim(), name, ambient=ambient_space, structure="Riemannian",
                     latex_name=latex_name, start_index=start_index)
        if names is None:
            names = tuple(f'x{i}' for i in range(self.dim()))
        CH = H.chart(names=names)

        data = self.affine_hull_projection(return_all_data=True, **kwds)
        projection_matrix = data.projection_linear_map.matrix().transpose()
        projection_translation_vector = data.projection_translation
        section_matrix = data.section_linear_map.matrix().transpose()
        section_translation_vector = data.section_translation

        from sage.symbolic.ring import SR
        # We use the slacks of the (linear independent) equations as the foliation parameters
        foliation_parameters = vector(SR.var(f't{i}') for i in range(self.ambient_dim() - self.dim()))
        normal_matrix = matrix(equation.A() for equation in self.equation_generator()).transpose()
        slack_matrix = normal_matrix.pseudoinverse()

        phi = H.diff_map(ambient_space, {(CH, CE):
                                         (section_matrix * vector(CH._xx) + section_translation_vector
                                          + normal_matrix * foliation_parameters).list()})
        phi_inv = ambient_space.diff_map(H, {(CE, CH):
                                             (projection_matrix * vector(CE._xx) + projection_translation_vector).list()})

        foliation_scalar_fields = {parameter:
                                   ambient_space.scalar_field({CE: slack_matrix.row(i) * (vector(CE._xx) - section_translation_vector)})
                                   for i, parameter in enumerate(foliation_parameters)}

        H.set_embedding(phi, inverse=phi_inv,
                        var=list(foliation_parameters), t_inverse=foliation_scalar_fields)
        return H

    def _affine_hull_name_latex_name(self, name=None, latex_name=None):
        r"""
        Return the default name of the affine hull.

        EXAMPLES::

            sage: polytopes.cube()._affine_hull_name_latex_name('C', r'\square')
            ('aff_C', '\\mathop{\\mathrm{aff}}(\\square)')

            sage: Polyhedron(vertices=[[0, 1], [1, 0]])._affine_hull_name_latex_name()
            ('aff_P', '\\mathop{\\mathrm{aff}}(P)')
        """

        if name is None:
            name = 'P'
        if latex_name is None:
            latex_name = name
        operator = 'aff'
        aff_name = f'{operator}_{name}'
        aff_latex_name = r'\mathop{\mathrm{' + operator + '}}(' + latex_name + ')'
        return aff_name, aff_latex_name

    def _polymake_init_(self):
        """
        Return a polymake "Polytope" object corresponding to ``self``.

        EXAMPLES::

            sage: P = polytopes.cube()
            sage: PP = polymake(P)         # optional - polymake
            sage: PP.N_VERTICES            # optional - polymake
            8

        Lower-dimensional polyhedron::

            sage: P = Polyhedron(vertices=[[1, 0], [0, 1]])
            sage: PP = polymake(P)         # optional - polymake
            sage: PP.COMBINATORIAL_DIM     # optional - polymake
            1
            sage: PP.AFFINE_HULL           # optional - polymake
            -1 1 1

        Empty polyhedron::

            sage: P = Polyhedron(ambient_dim=2, vertices=[])
            sage: PP = polymake(P)         # optional - polymake
            sage: PP.COMBINATORIAL_DIM     # optional - polymake
            -1

        Pointed unbounded polyhedron::

            sage: P = Polyhedron(vertices=[[1, 0], [0, 1]], rays=[[1, 0]])
            sage: PP = polymake(P)         # optional - polymake
            sage: PP.VERTICES              # optional - polymake
            1 0 1
            1 1 0
            0 1 0
            sage: PP.FACETS                # optional - polymake
            1 0 -1
            -1 1 1
            0 0 1

        Non-pointed polyhedron::

            sage: P = Polyhedron(vertices=[[1, 0], [0, 1]], lines=[[1, 0]])
            sage: PP = polymake(P)         # optional - polymake
            sage: PP.VERTICES              # optional - polymake
            1 0 1
            1 0 0
            sage: PP.FACETS                # optional - polymake
            1 0 -1
            0 0 1
            sage: PP.LINEALITY_SPACE       # optional - polymake
            0 1 0

        Algebraic polyhedron::

            sage: P = polytopes.dodecahedron(); P                                                             # optional - sage.rings.number_field
            A 3-dimensional polyhedron
             in (Number Field in sqrt5 with defining polynomial x^2 - 5
                 with sqrt5 = 2.236067977499790?)^3
             defined as the convex hull of 20 vertices
            sage: print("There may be a recompilation warning"); PP = polymake(P); PP  # optional - polymake  # optional - sage.rings.number_field
            There may be a recompilation warning...
            Polytope<QuadraticExtension<Rational>>[...]
            sage: sorted(PP.VERTICES[:], key=repr)[0]                                  # optional - polymake  # optional - sage.rings.number_field
            1 -1+1r5 -4+2r5 0

        Floating-point polyhedron::

            sage: P = polytopes.dodecahedron(exact=False); P
            A 3-dimensional polyhedron in RDF^3 defined as the convex hull of 20 vertices
            sage: print("There may be a recompilation warning"); PP = polymake(P); PP # optional - polymake
            There may be a recompilation warning...
            Polytope<Float>[...]
            sage: sorted(PP.VERTICES[:], key=repr)[0] # optional - polymake
            1 -0.472135955 0 -1.236067978

        """
        from sage.interfaces.polymake import polymake
        polymake_field = polymake(self.base_ring().fraction_field())
        polymake_class = "Polytope<{}>".format(polymake_field)
        if self.is_empty():
            # Polymake 3.1 cannot enter an empty polyhedron using
            # FACETS and AFFINE_HULL.  Use corresponding input properties instead.
            # https://forum.polymake.org/viewtopic.php?f=8&t=545
            return polymake.new_object(polymake_class,
                                       INEQUALITIES=self.inequalities_list(),
                                       EQUATIONS=self.equations_list())
        else:
            return polymake.new_object(polymake_class,
                                       FACETS=self.inequalities_list(),
                                       AFFINE_HULL=self.equations_list(),
                                       VERTICES=   [ [1] + v for v in self.vertices_list() ] \
                                                 + [ [0] + r for r in self.rays_list() ],
                                       LINEALITY_SPACE=[ [0] + l for l in self.lines_list() ])
