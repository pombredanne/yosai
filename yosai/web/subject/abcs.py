"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from abc import abstractmethod

from yosai.core import (
    subject_abcs,
)


class WebSubject(subject_abcs.Subject):

    @property
    @abstractmethod
    def web_registry(self):
        pass

    @web_registry.setter
    @abstractmethod
    def web_registry(self, web_registry):
        pass


class WebSubjectContext(subject_abcs.SubjectContext):

    @property
    @abstractmethod
    def web_registry(self):
        pass

    @web_registry.setter
    @abstractmethod
    def web_registry(self, web_registry):
        pass

    @abstractmethod
    def resolve_web_registry(self):
        pass
