"""
Import an IFC file and turn it into a Honeybee model.
Currently, only supporting IFC files with IFC2x3 schema.
"""
import pathlib
import multiprocessing

import ifcopenshell
from ifcopenshell.util.unit import calculate_unit_scale
from ifcopenshell.util.placement import get_local_placement
from ifcopenshell.util.selector import Selector

from honeybee.model import Model as HBModel

from .wall import Wall
from .window import Window
from .door import Door
from .slab import Slab
from .shade import Shade
from .space import Space


class Model:
    """Honeybee-IFC model.

    Args:
        ifc_file_path: A string. The path to the IFC file.
    """

    def __init__(self, ifc_file_path: str) -> None:
        self.ifc_file_path = self._validate_path(ifc_file_path)
        self.ifc_file = ifcopenshell.open(self.ifc_file_path)
        self.settings = self._ifc_settings()
        self.unit_factor = calculate_unit_scale(self.ifc_file)
        self.elements = ('IfcSlab', 'IfcColumn', 'IfcWindow', 'IfcDoor', 'IfcSpace')
        self.spaces = []
        self.doors = []
        self.windows = []
        self.slabs = []
        self.walls = []
        self.shades = []
        self._extract_walls()
        self._extract_elements()

    @staticmethod
    def _validate_path(path: str) -> pathlib.Path:
        """Validate path."""
        path = pathlib.Path(path)
        if not path.exists():
            raise ValueError(f'Path {path} does not exist.')
        return path

    @staticmethod
    def _ifc_settings() -> ifcopenshell.geom.settings:
        """IFC settings."""
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.USE_BREP_DATA, True)
        return settings

    def _extract_elements(self) -> None:
        """Extract elements from the IFC file."""
        iterator = ifcopenshell.geom.iterator(
            self.settings, self.ifc_file, multiprocessing.cpu_count(),
            include=self.elements)

        if iterator.initialize():
            while iterator.next():
                shape = iterator.get()
                element = self.ifc_file.by_guid(shape.guid)

                if element.is_a() == 'IfcWindow':
                    self.windows.append(Window(element, self.settings))

                elif element.is_a() == 'IfcDoor':
                    self.doors.append(Door(element, self.settings))

                elif element.is_a() == 'IfcSlab':
                    self.slabs.append(
                        Slab(element, element.PredefinedType, self.settings))

                elif element.is_a() == 'IfcColumn':
                    self.shades.append(
                        Shade(element, self.settings))

                elif element.is_a() == 'IfcSpace':
                    self.spaces.append(Space(element, self.settings))

                else:
                    raise ValueError(f'Unsupported element type: {element.is_a()}')

    def _extract_walls(self) -> None:
        """Extract IfcWall elements from the IFC file."""
        # Don't use BREP data here. Which will give original trinagulated meshes.
        selector = Selector()
        self.walls = [Wall(element) for element in selector.parse(
            self.ifc_file, '.IfcWall | .IfcWallStandardCase')]

    def to_hbjson(self, target_folder: str = '.', file_name: str = None) -> str:
        """Write the model to an HBJSON file.

        Args:
            target_folder: The folder where the HBJSON file will be saved.
                Default to the current working directory.
            file_name: The name of the HBJSON file. Default to the name of the
                IFC file.

        Returns:
            Path to the written HBJSON file.
        """

        faces = []
        for wall in self.walls:
            faces.extend(wall.to_honeybee())

        apertures = [window.to_honeybee() for window in self.windows]
        doors = [door.to_honeybee() for door in self.doors]

        for slab in self.slabs:
            faces.extend(slab.to_honeybee())

        shades = []
        for shade in self.shades:
            shades.extend(shade.to_honeybee())

        grids = []
        for space in self.spaces:
            grids.append(space.get_grids(size=0.3))

        hb_model = HBModel('Model', orphaned_faces=faces,
                           orphaned_apertures=apertures, orphaned_doors=doors,
                           orphaned_shades=shades)

        hb_model.properties.radiance.add_sensor_grids(grids)

        if not file_name:
            file_name = self.ifc_file_path.stem

        path = hb_model.to_hbjson(name=file_name, folder=target_folder)

        return path
